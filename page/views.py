# the module for the django project.
from django.shortcuts import render, redirect, HttpResponse
from .models import *
from django.contrib import messages
from django.db import connection
from datetime import date, datetime, timedelta
from .function_list import *
from .serializer import LocationTrackSerializer
from rest_framework.views import APIView
from .threading import SaveAttendanceThread
from rest_framework.response import Response
from django.contrib.auth import logout as lout
import xlwt
from django.template.loader import get_template
from xhtml2pdf import pisa


# this function redirects to the main page.
def homepage(request):
    SaveAttendanceThread().start()
    return render(request, "homepage.html", {'title': 'Homepage'})


def logout(request):
    lout(request=request)
    return render(request, "logout.html", {'title': 'Logout'})


class TagApiView(APIView):
    serializer_class = LocationTrackSerializer

    def get(self, request, *args, **kwargs):
        if len(kwargs) == 2:
            area = kwargs['area_']
            tag_id = kwargs['tag_']
        else:
            area = None
            tag_id = None
        obj_id = LocationTrack.objects.filter(tag_id_id=tag_id, date=date.today()).order_by('-time')
        data = LocationTrackSerializer(obj_id, many=True)
        if not tag_id or not area:
            return Response(data.data)
        if area and tag_id:
            cursor = connection.cursor()
            cursor.execute(f"select max(date) from page_locationtrack where tag_id_id='{tag_id}';")
            previous_visited_date = cursor.fetchone()

            # checking the IN/OUT status for the student
            if previous_visited_date[0] != date.today():
                # if new day, then status should be IN
                status = 'IN'
            else:
                # if already has entry in database for the day
                cursor = connection.cursor()
                cursor.execute(f"""select area, status from page_locationtrack where tag_id_id = '{tag_id}' 
                        and time=(select max(time) from page_locationtrack where tag_id_id = '{tag_id}' 
                        and date=(select max(date) from page_locationtrack where tag_id_id='{tag_id}'));""")
                previous_visited_place, status = cursor.fetchone()

                if previous_visited_place == area and status == 'IN':
                    status = 'OUT'
                elif previous_visited_place == area and status == 'OUT':
                    status = 'IN'
                else:
                    status = 'IN'

            # saving the responses to database
            entry = LocationTrack()
            entry.area = area
            entry.tag_id_id = tag_id
            entry.status = status
            entry.save()
        return Response(data.data)


def analyse_attendance(request):
    content = {'course': []}
    cursor = connection.cursor()
    cursor.execute('select distinct(page_attendancerecord.course) from page_attendancerecord;')
    courses = cursor.fetchall()
    course_attendance = []
    for course in courses:
        cursor.execute(f'''select sum(distinct(page_attendancerecord.attendance_count)) from page_attendancerecord 
                            where page_attendancerecord.course ='{course[0]}';''')
        count = cursor.fetchone()
        if count:
            course_attendance.append(int(count[0]))
        else:
            course_attendance.append(0)
    content['course'].append(courses)
    content['course'].append(course_attendance)
    return render(request, 'analyse.html', content)


def view_timetable(request):
    content = {'head': ['COURSE', 'YEAR', 'PLACE', 'START TIME', 'END TIME',
                        'MON', 'TUE', 'WED', 'THUR', 'FRI', 'SAT', 'SUN'],
               'course': {}}
    cursor = connection.cursor()
    cursor.execute('select distinct(page_timetable.course) from page_timetable;')
    courses = cursor.fetchall()

    if courses:
        for course in courses:

            cursor.execute(f'''select page_timetable.course, page_timetable.year, 
                                page_timetable.area, page_timetable.start_time, page_timetable.end_time,
                                page_timetable."Monday",page_timetable."Tuesday",page_timetable."Wednesday",
                                page_timetable."Thursday",page_timetable."Friday",page_timetable."Saturday",
                                page_timetable."Sunday" from page_timetable where page_timetable.course = '{course[0]}'
                                order by page_timetable.course ; ''')
            content['course'][f'{course[0]}'] = cursor.fetchall()

    else:
        messages.error(request, 'No timetable to show!')
    return render(request, 'view.html', content)


def weekly_monthly_excel_pdf(request, method=None):
    today = request.GET.get('date')
    previous_date = request.GET.get('end_date')

    today = today.split('-')
    previous_date = previous_date.split('-')
    today = date(int(today[0]), int(today[1]), int(today[2]))
    previous_date = date(int(previous_date[0]), int(previous_date[1]), int(previous_date[2]))

    table_head = ['Start_time', 'End_time', 'Date', 'Day', 'Count', 'Tag ID', 'Name', 'Div', 'Roll', 'Area']
    cursor = connection.cursor()
    cursor.execute(f'select distinct(page_attendancerecord.course) from page_attendancerecord ;')
    courses = cursor.fetchall()
    content = {'table_head': table_head, 'courses': {}, 'today': str(today),
               'last_date': str(previous_date),
               'title': 'weekly records'}

    if (today - previous_date).days > 7:
        content['root'] = 'M'
    else:
        content['root'] = 'W'

    for course in courses:
        content['courses'][f'{course[0]}'] = {}
        cursor.execute(f"""select distinct(page_attendancerecord.attendance_batch) 
                                    from page_attendancerecord where page_attendancerecord.course = '{course[0]}';""")
        batches = cursor.fetchall()

        for batch in batches:
            content['courses'][f'{course[0]}'][f'{batch[0]}'] = []

            cursor.execute(f"""select page_attendancerecord.start_time, page_attendancerecord.end_time, 
                                        page_attendancerecord.attendance_date, page_attendancerecord.attendance_day, 
                                        page_attendancerecord.attendance_count, page_attendancerecord.tag_id, 
                                        page_attendancerecord.std_name, 
                                        page_attendancerecord.std_div, page_attendancerecord.std_roll, 
                                        page_attendancerecord.attendance_location from page_attendancerecord where
                                        page_attendancerecord.attendance_date >= '{previous_date}' and 
                                        page_attendancerecord.attendance_date <= '{today}' and 
                                        page_attendancerecord.attendance_batch = '{batch[0]}';""")
            records = cursor.fetchall()
            content['courses'][f'{course[0]}'][f'{batch[0]}'].append(records)

    if method == '1':
        try:
            # initializing the excel
            response = HttpResponse(content_type='application/ms-excel')
            # setting filename
            # response['Content-Disposition'] = 'filename=filename.xls'   ##### for viewing the excel online
            # response['Content-Disposition'] = 'attachment; filename=filename.xls'   ##### for downloading the excel
            response['Content-Disposition'] = f'attachment; filename=rfid-{date.today()}.xls'
            wb = xlwt.Workbook(encoding='utf-8')
            # adding the sheet name
            ws = wb.add_sheet(f'({today})-({previous_date})')

            # setting font style and type
            font_style = xlwt.XFStyle()
            font_style.font.bold = True
            row_num = 1
            ws.write(row_num, 0, 'Records for', font_style)
            ws.write(row_num, 1, f'{today}', font_style)
            ws.write(row_num, 2, '-', font_style)
            ws.write(row_num, 3, f'{previous_date}', font_style)
            row_num += 3

            # inputting data into the excel (according to the number of sheets in the excel)
            for course, data in content['courses'].items():
                ws.write(row_num, 1, f'{course}', font_style)
                row_num += 1
                for batches, records in data.items():
                    ws.write(row_num, 1, f'{batches}', font_style)
                    for col, head in enumerate(content['table_head'], start=2):
                        ws.write(row_num, col, f'{head}', font_style)
                    row_num += 1
                    for std in records:
                        for std_details in std:
                            ws.write(row_num, 1, '', font_style)
                            for col, m in enumerate(std_details, start=2):
                                ws.write(row_num, col, f'{m}', font_style)
                            row_num += 1
                        row_num += 1
                    row_num += 1
                row_num += 3
            wb.save(response)
            return response
        except:
            messages.error(request, 'something went wrong please try again!')
            if content['root'] == 'M':
                return redirect('/monthly_data/')
            else:
                return redirect('/weekly_data/')
    elif method == '2':
        # try:
        # giving template path along with name
        template_path = 'weekly_monthly_pdf.html'
        # initializing pdf
        response = HttpResponse(content_type='application/pdf')
        # setting filename
        # response['Content-Disposition'] = 'filename=filename.xls'   ##### for viewing the excel online
        # response['Content-Disposition'] = 'attachment; filename=filename.xls'   ##### for downloading the excel
        response['Content-Disposition'] = f'attachment; filename="rfid-{date.today()}.pdf"'
        template = get_template(template_path)
        html = template.render(content)
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response
        '''except:
        messages.error(request, 'something went wrong please try again!')
        if content['root'] == 'M':
            return redirect('/monthly_data/')
        else:
            return redirect('/weekly_data/')'''


def monthly_data(requests):
    if requests.method == 'GET':

        user_date = requests.GET.get('DATE')
        table_head = ['Start_time', 'End_time', 'Date', 'Day', 'Count', 'Tag ID', 'Name', 'Div', 'Roll', 'Area']
        cursor = connection.cursor()
        cursor.execute(f'select distinct(page_attendancerecord.course) from page_attendancerecord ;')
        courses = cursor.fetchall()

        if not user_date:
            today = date.today()
        else:
            user_date = user_date.split('-')
            today = date(int(user_date[0]), int(user_date[1]), int(user_date[2]))

        previous_date = today.replace(day=1)
        if today == previous_date:
            previous_date = str(previous_date).split('-')
            if int(previous_date[1]) == 1:
                previous_month = 12
            else:
                previous_month = int(previous_date[1]) - 1
            previous_date = date(int(previous_date[0]), int(previous_month), int(previous_date[2]))

        content = {'table_head': table_head, 'courses': {}, 'today': str(today),
                   'last_date': str(previous_date),
                   'title': 'Monthly records'}

        for course in courses:
            content['courses'][f'{course[0]}'] = {}
            cursor.execute(f"""select distinct(page_attendancerecord.attendance_batch) 
                                from page_attendancerecord where page_attendancerecord.course = '{course[0]}';""")
            batches = cursor.fetchall()

            for batch in batches:
                content['courses'][f'{course[0]}'][f'{batch[0]}'] = []

                cursor.execute(f"""select page_attendancerecord.start_time, page_attendancerecord.end_time, 
                                    page_attendancerecord.attendance_date, page_attendancerecord.attendance_day, 
                                    page_attendancerecord.attendance_count, page_attendancerecord.tag_id, 
                                    page_attendancerecord.std_name, 
                                    page_attendancerecord.std_div, page_attendancerecord.std_roll, 
                                    page_attendancerecord.attendance_location from page_attendancerecord where
                                    page_attendancerecord.attendance_date >= '{previous_date}' and 
                                    page_attendancerecord.attendance_date <= '{today}' and 
                                    page_attendancerecord.attendance_batch = '{batch[0]}';""")
                records = cursor.fetchall()
                content['courses'][f'{course[0]}'][f'{batch[0]}'].append(records)
        content['date'] = get_date()
        return render(requests, 'weekly.html', content)
    return render(requests, 'weekly.html', {'date': get_date(), 'title': 'Monthly data'})


def weekly_data(requests):
    if requests.method == 'GET':

        user_date = requests.GET.get('DATE')
        table_head = ['Start_time', 'End_time', 'Date', 'Day', 'Count', 'Tag ID', 'Name', 'Div', 'Roll', 'Area']
        cursor = connection.cursor()
        cursor.execute(f'select distinct(page_attendancerecord.course) from page_attendancerecord ;')
        courses = cursor.fetchall()

        if not user_date:
            today = date.today()
        else:
            user_date = user_date.split('-')
            today = date(int(user_date[0]), int(user_date[1]), int(user_date[2]))

        previous_date = today - timedelta(days=7)

        content = {'table_head': table_head, 'courses': {}, 'today': str(today),
                   'last_date': str(previous_date),
                   'title': 'weekly records'}

        for course in courses:
            content['courses'][f'{course[0]}'] = {}
            cursor.execute(f"""select distinct(page_attendancerecord.attendance_batch) 
                                from page_attendancerecord where page_attendancerecord.course = '{course[0]}';""")
            batches = cursor.fetchall()

            for batch in batches:
                content['courses'][f'{course[0]}'][f'{batch[0]}'] = []

                cursor.execute(f"""select page_attendancerecord.start_time, page_attendancerecord.end_time, 
                                    page_attendancerecord.attendance_date, page_attendancerecord.attendance_day, 
                                    page_attendancerecord.attendance_count, page_attendancerecord.tag_id,
                                    page_attendancerecord.std_name, 
                                    page_attendancerecord.std_div, page_attendancerecord.std_roll, 
                                    page_attendancerecord.attendance_location from page_attendancerecord where
                                    page_attendancerecord.attendance_date >= '{previous_date}' and 
                                    page_attendancerecord.attendance_date <= '{today}' and 
                                    page_attendancerecord.attendance_batch = '{batch[0]}';""")
                records = cursor.fetchall()
                content['courses'][f'{course[0]}'][f'{batch[0]}'].append(records)
        content['date'] = get_date()
        return render(requests, 'weekly.html', content)
    return render(requests, 'weekly.html', {'date': get_date(), 'title': 'weekly data'})


# this function register new student/teacher in the database
def register_data(request):
    if request.method == 'POST':
        # getting all the html variables
        first_name = request.POST.get('FIRST_NAME')
        last_name = request.POST.get('LAST_NAME')
        tag_id = request.POST.get('TAG_ID')
        course = request.POST.get('course')
        year = request.POST.get('year')
        roll = request.POST.get('ROLL_NO')
        div = request.POST.get('DIVISION')
        if div:
            div = div.upper()

        # render message to input course field
        if first_name and last_name and tag_id and roll and div and not course:
            messages.error(request, "choose course!")
            return render(request, "register.html")
        if first_name and last_name and tag_id and roll and div and not year:
            messages.error(request, "choose academic year!")
            return render(request, "register.html")
        if first_name and last_name and tag_id and course and year and roll and div:
            # query to check is the tag id registered in the database
            cursor = connection.cursor()
            cursor.execute(f"select tag_id from page_register where tag_id='{tag_id}'")
            tag_id_copy = cursor.fetchone()
            if tag_id_copy:
                # id not a registered tag id
                if tag_id == tag_id_copy[0]:
                    messages.error(request, "the Tag Id is already taken")
                    return render(request, "register.html", {'title': 'Register'})

            # if a registered tag id then register in the database
            register = Register()
            register.name = first_name + " " + last_name
            register.tag_id = tag_id
            register.course = course
            register.year = year
            register.roll = roll
            register.div = div
            register.save()
            messages.success(request, "registered successfully!")
            return render(request, "register.html", {'message': 'registered', 'title': 'Register'})
    return render(request, "register.html", {'title': 'Register'})


# this function accepts tag id and area of the tag id where it was tapped and enter it in the database
def entry_data(request):
    if request.method == "GET":
        # getting the html variables
        area = request.GET.get("AREA")
        tag_id = request.GET.get('TAG_ID')

        # checking is the tag_id registered or not
        if tag_id:
            cursor = connection.cursor()
            cursor.execute(f"select tag_id from page_register where tag_id='{tag_id}'")
            tag = cursor.fetchone()
            if not tag:
                cursor = connection.cursor()
                cursor.execute(f"select tag_id from page_teacherregister where tag_id='{tag_id}'")
                tag = cursor.fetchone()
        else:
            tag = None

        # sending appropriate messages
        if not area or not tag_id:
            messages.error(request, "enter fields correctly")
            return render(request, 'entry.html')
        if not tag:
            messages.error(request, "Unregistered TagId")
            return render(request, 'entry.html')
        # if tag id is registered in the database
        if area and tag_id:
            cursor = connection.cursor()
            cursor.execute(f"select max(date) from page_locationtrack where tag_id_id='{tag_id}';")
            previous_visited_date = cursor.fetchone()

            # checking the IN/OUT status for the student
            if previous_visited_date[0] != date.today():
                # if new day, then status should be IN
                status = 'IN'
            else:
                # if already has entry in database for the day
                cursor = connection.cursor()
                cursor.execute(f"""select area, status from page_locationtrack where tag_id_id = '{tag_id}' 
                and time=(select max(time) from page_locationtrack where tag_id_id = '{tag_id}' 
                and date=(select max(date) from page_locationtrack where tag_id_id='{tag_id}'));""")
                previous_visited_place, status = cursor.fetchone()

                if previous_visited_place == area and status == 'IN':
                    status = 'OUT'
                elif previous_visited_place == area and status == 'OUT':
                    status = 'IN'
                else:
                    status = 'IN'

            # saving the responses to database
            entry = LocationTrack()
            entry.area = area
            entry.tag_id_id = tag_id
            entry.status = status
            entry.save()

            messages.success(request, "Successfully submitted")
    return render(request, 'entry.html')


# this function keep track of a particular tag id for a particular day
def trace_card(request, method='<1>'):
    # getting distinct dates from database :- function_list.py
    date_list = get_date()

    if request.method == "GET":
        table_data = []
        # taking html variables
        tag_id_ = request.GET.get('TAG_ID')
        user_date = request.GET.get('DATE')
        roll_number = request.GET.get('roll_no')
        division = request.GET.get('division')

        if division:
            division = division.upper()

        course = request.GET.get('course')
        t_name = request.GET.get('t_name')
        tag_origin = None
        # setting user_date (if inputted or not)
        if user_date:
            user_date = convert_date(user_date)
        else:
            user_date = date.today()

        cursor = connection.cursor()
        # checking that the submitted data is for teacher.
        if method[1] == '3':

            if t_name:
                cursor.execute(f"""select page_teacherregister.tag_id from page_teacherregister 
                               where page_teacherregister.t_name = '{t_name}';""")
                tag_id_ = cursor.fetchone()[0]

        # checking that the submitted data is in roll - div format
        if method[1] == '2':

            if not course:
                messages.error(request, 'Enter fields correctly')
                return render(request, 'trace.html',
                              {'title': 'Trace', "date": date_list, 't_list': teacher_list()})
            cursor.execute(f"""select page_register.tag_id from page_register where 
                           page_register.roll = '{roll_number}' and page_register.div = '{division}' and
                           page_register.course = '{course}';""")
            tag_id_ = cursor.fetchone()
            if tag_id_:
                tag_id_ = tag_id_[0]
            else:
                messages.error(request, 'Invalid Inputs')
                return render(request, 'trace.html',
                              {'title': 'Trace', "date": date_list, 't_list': teacher_list()})

        # checking whether tag id is registered
        if tag_id_:

            cursor.execute(f"select * from page_register where page_register.tag_id ='{tag_id_}';")
            is_valid_tag = cursor.fetchone()
            tag_origin = 'student'
            if not is_valid_tag:
                cursor = connection.cursor()
                cursor.execute(f"select * from page_teacherregister where page_teacherregister.tag_id ='{tag_id_}';")
                is_valid_tag = cursor.fetchone()
                tag_origin = 'teacher'
        else:
            return render(request, "trace.html", {"date": date_list, 'title': 'Trace', 't_list': teacher_list()})

        # getting person class instance for given tag id :- models.py
        if tag_origin == 'student':
            person = Register.objects.filter(tag_id=tag_id_)
        else:
            person = TeacherRegister.objects.filter(tag_id=tag_id_)

        # getting track details for the tag id in an ordered manner by time
        cursor.execute(
            f"""select area,time,status from page_locationtrack where tag_id_id='{tag_id_}' and date='{user_date}' 
                       order by time;""")
        data = cursor.fetchall()

        # adding serial number at starting of each list
        for x, (area, time, status) in enumerate(data, 1):
            table_data.append([x, area, time, status])
        if tag_id_:
            if person:
                if tag_origin == 'student':
                    return render(request, 'trace.html',
                                  {"table_data": table_data, "person_data": person, "date": date_list,
                                   'user_date': str(user_date), 'origin': 'student', 'title': 'Trace',
                                   't_list': teacher_list()})
                else:
                    return render(request, 'trace.html',
                                  {"table_data": table_data, "person_data": person, "date": date_list,
                                   'user_date': str(user_date), 'origin': 'teacher', 'title': 'Trace',
                                   't_list': teacher_list()})
            # if not registered tag id
            if not is_valid_tag:
                messages.error(request, "Invalid Tag Id")
                return render(request, "trace.html", {"date": date_list, 'title': 'Trace', 't_list': teacher_list()})

    return render(request, "trace.html", {"date": date_list, 'title': 'Trace', 't_list': teacher_list()})


# this function make student count in time wise manner
def time_wise_count(request):
    # getting distinct dates from database
    date_list = get_date()

    if request.method == "GET":
        # getting html variables
        place_to_find_count = request.GET.get('AREA')
        start_time = request.GET.get("START_TIME")
        start_minute = request.GET.get("START_MINUTE")
        end_time = request.GET.get("LAST_TIME")
        end_minute = request.GET.get("END_MINUTE")
        user_date = request.GET.get('DATE')

        # setting user date (if inputted or not)
        if user_date:
            user_date = convert_date(user_date)
        else:
            user_date = date.today()

        # getting content for particular area for entire day
        if place_to_find_count and not start_time and not end_time:
            # getting content :- function_list.py
            message, content = count_for_entire_day(place_to_find_count,
                                                    user_date, start_minute, end_minute)
            # adding extra content (required for pdf/excel download)
            extra_content = {'area': place_to_find_count, 'start_time': start_time, 'start_minute': start_minute,
                             'end_time': end_time, 'end_minute': end_minute, 'user_date': str(user_date),
                             'date': date_list, 'title': 'Time-Count'}
            # adding 2 dict
            content.update(extra_content)
            messages.success(request, message)
            return render(request, 'count.html', content)

        # getting content for particular area with starting time
        if place_to_find_count and start_time and not end_time:
            # getting content :- function_list.py
            message, content = count_with_starting_time(start_minute, start_time,
                                                        place_to_find_count, user_date)
            # adding extra content (required for excel/pdf download)
            extra_content = {'area': place_to_find_count, 'start_time': start_time, 'start_minute': start_minute,
                             'end_time': end_time, 'end_minute': end_minute, 'user_date': str(user_date),
                             'date': date_list, 'title': 'Time-Count'}
            # adding 2 dict
            content.update(extra_content)
            messages.success(request, message)
            return render(request, 'count.html', content)

        # getting content for particular area with ending time
        if place_to_find_count and not start_time and end_time:
            # getting content  :- function_list.py
            message, content = count_with_ending_time(end_minute, end_time, place_to_find_count, user_date)
            # adding extra content (required for excel/pdf download)
            extra_content = {'area': place_to_find_count, 'start_time': start_time, 'start_minute': start_minute,
                             'end_time': end_time, 'end_minute': end_minute, 'user_date': str(user_date),
                             'date': date_list, 'title': 'Time-Count'}
            # adding 2 dict
            content.update(extra_content)
            messages.success(request, message)
            return render(request, 'count.html', content)

        # getting content for particular area with start and end time limits
        if place_to_find_count and start_time and end_time:
            # getting content :- function_list.py
            content = count_with_start_end_time(start_minute, end_minute, start_time,
                                                end_time, place_to_find_count, user_date)
            # adding extra content (required foe excel/pdf download)
            extra_content = {'area': place_to_find_count, 'start_time': start_time, 'start_minute': start_minute,
                             'end_time': end_time, 'end_minute': end_minute, 'user_date': str(user_date),
                             'date': date_list, 'title': 'Time-Count'}
            # adding 2 dict
            content.update(extra_content)
            # setting minutes for appropriate message
            if not start_minute:
                start_minute = 00
            if not end_minute:
                end_minute = 00
            message = f'showing feed for {start_time}:{start_minute} to {end_time}:{end_minute}'
            messages.success(request, message)

            return render(request, 'count.html', content)
    return render(request, 'count.html', {"date": date_list, 'title': 'Time-Count'})


# this function redirects the time_wise/timetable_wise count html page
def count_person(request):
    return render(request, 'count_selection.html')


# this above function is not in use


# this function make student count in accordance to the timetable
def timetable_wise_count(request):
    # getting distinct date from database
    date_list = get_date()
    content = {}

    if request.method == "GET":
        # getting html variables
        course = request.GET.get('course')
        user_date = request.GET.get('DATE')

        # giving appropriate message to select
        if not course and user_date:
            messages.error(request, "please select Course")
            return render(request, 'timetable.html', {'date': date_list, 'title': 'TimeTable-Count'})

        # setting user date (if inputted or not)
        if user_date:
            user_date = convert_date(user_date)
            split_list_of_date = user_date.split('-')
            day = date(int(split_list_of_date[0]), int(split_list_of_date[1]), int(split_list_of_date[2]))
            day = day.strftime('%A')
        else:
            day = datetime.today().strftime("%A")
            user_date = date.today()

        # extracting data from excel file regarding the given course
        if course:
            cursor = connection.cursor()
            cursor.execute(f'''select distinct(page_timetable.year) from page_timetable where course='{course}';''')
            years = cursor.fetchall()

            iteration = 1
            for year in years:
                cursor = connection.cursor()
                cursor.execute(f'''select page_timetable.start_time,page_timetable.end_time,page_timetable.area,
                page_timetable."{day}" from page_timetable where course='{course}' and 
                year='{year[0]}';''')
                year_data = cursor.fetchall()
                ret_values = return_count_value(year_data, user_date)
                content[f'dist_count{iteration}'] = ret_values[0]
                content[f'person_list{iteration}'] = ret_values[1]
                content[f'table{iteration}'] = ret_values[2]
                content[f'batch_time{iteration}'] = ret_values[3]
                content[f'area{iteration}'] = ret_values[4]

                content[f'head{iteration}'] = year[0]

                iteration += 1

            # getting filtered content form excel
            # content = render_course_data(user_date, timetable, day, len(timetable))
            # adding extra content (required for excel/pdf download)
            extra_content = {'date': date_list, 'user_date': str(user_date), 'course': course, 'day': day,
                             'title': 'TimeTable-Count'}
            # adding 2 dict
            content.update(extra_content)
            messages.success(request, f'showing Attendance for {user_date}')
            return render(request, 'timetable.html', content)
    return render(request, 'timetable.html', {'date': date_list, 'title': 'TimeTable-Count'})


# this function make the excel for trace of tag id
def trace_excel(request):
    # setting try/except so that website don't crash if any error occured while making the excel
    try:
        # obtaining the get request data
        tag_id = request.GET.get('TAG_ID')
        user_date = request.GET.get('DATE')

        if tag_id:
            cursor = connection.cursor()
            cursor.execute(f"select * from page_register where page_register.tag_id ='{tag_id}';")
            is_valid_tag = cursor.fetchone()
            tag_origin = 'student'
            if not is_valid_tag:
                cursor = connection.cursor()
                cursor.execute(f"select * from page_teacherregister where page_teacherregister.tag_id ='{tag_id}';")
                is_valid_tag = cursor.fetchone()
                tag_origin = 'teacher'

        # initializing the excel
        response = HttpResponse(content_type='application/ms-excel')
        # setting filename
        # response['Content-Disposition'] = 'filename=filename.xls'   ##### for viewing the excel online
        # response['Content-Disposition'] = 'attachment; filename=filename.xls'   ##### for downloading the excel
        response['Content-Disposition'] = f'attachment; filename={tag_id}-{date.today()}.xls'
        wb = xlwt.Workbook(encoding='utf-8')
        # adding sheet name
        ws = wb.add_sheet(f'trace {tag_id}')
        row_num = 1
        # setting font style and type
        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        ws.write(row_num, 0, 'Showing Trace Data for', font_style)
        ws.write(row_num, 1, str(user_date), font_style)
        row_num += 2
        # getting person details from the given tag id (getting list instead of class instance)
        if tag_origin == 'student':
            person = Register.objects.filter(tag_id=tag_id).values_list('tag_id', 'div', 'roll',
                                                                        'name', 'course', 'year')
        else:
            person = TeacherRegister.objects.filter(tag_id=tag_id).values_list('tag_id', 'practical_subject',
                                                                               't_name', 'course')

        person = person[0]

        if tag_origin == 'student':
            details = ['Tag id', 'Division', 'Roll number', 'Name', 'Course', 'Academic year']
            for i in range(len(details)):
                row_num += 1
                ws.write(row_num, 0, details[i], font_style)
                ws.write(row_num, 1, str(person[i]), font_style)
        else:
            details = ['Tag id', 'Practical Subject', 'Name', 'Course']
            for i in range(len(details)):
                row_num += 1
                ws.write(row_num, 0, details[i], font_style)
                ws.write(row_num, 1, str(person[i]), font_style)

        row_num = row_num + 2
        ws.write(row_num, 0, 'Trace Table', font_style)
        font_style.font.bold = False

        # getting track details for the tag id in an order manner to time
        cursor = connection.cursor()
        cursor.execute(
            f"""select area,time,status from page_locationtrack where tag_id_id='{tag_id}' 
                and date='{user_date}' order by time;""")
        table_data = cursor.fetchall()

        row_num += 1
        table_heading = ['Sr No', 'Area', 'Time', 'Status']
        for sr_no, heading in enumerate(table_heading, 0):
            ws.write(row_num, sr_no, heading, font_style)
        row_num += 1
        # inserting data into the table
        for srno, (area, data_time, status) in enumerate(table_data, 1):
            row_num += 1
            ws.write(row_num, 0, srno, font_style)
            ws.write(row_num, 1, area, font_style)
            ws.write(row_num, 2, str(data_time), font_style)
            ws.write(row_num, 3, str(status), font_style)
        wb.save(response)
        return response
    except:
        messages.error(request, 'something went wrong please try again!')
        return redirect('/trace/')


# this function makes time_wise count excel
def time_wise_excel(request):
    # settign try/except for the website to not to crash by any error occurance
    try:

        # obtaining the get request data
        place_to_find_count = request.GET.get('area')
        start_time = request.GET.get("s_t")
        start_minute = request.GET.get("s_m")
        end_time = request.GET.get("e_t")
        end_minute = request.GET.get("e_m")
        user_date = request.GET.get('date')

        # getting content for particular area for entire day
        if place_to_find_count and not start_time and not end_time:
            message, content = count_for_entire_day(place_to_find_count,
                                                    user_date, start_minute, end_minute)

        # getting content for particular area and start time
        if place_to_find_count and start_time and not end_time:
            message, content = count_with_starting_time(start_minute, start_time,
                                                        place_to_find_count, user_date)

        # getting content for particular area and end time
        if place_to_find_count and not start_time and end_time:
            message, content = count_with_ending_time(end_minute, end_time, place_to_find_count, user_date)

        # getting content for particular area with start and end time limit
        if place_to_find_count and start_time and end_time:
            content = count_with_start_end_time(start_minute, end_minute, start_time,
                                                end_time, place_to_find_count, user_date)
            # initializing the minutes for appropriate message
            if not start_minute:
                start_minute = 00
            if not end_minute:
                end_minute = 00
            message = f'showing feed for {start_time}:{start_minute} to {end_time}:{end_minute}'

        # initializing the excel
        response = HttpResponse(content_type='application/ms-excel')
        # setting filename
        # response['Content-Disposition'] = 'filename=filename.xls'   ##### for viewing the excel online
        # response['Content-Disposition'] = 'attachment; filename=filename.xls'   ##### for downloading the excel
        response['Content-Disposition'] = f'attachment; filename={place_to_find_count}-{date.today()}.xls'
        wb = xlwt.Workbook(encoding='utf-8')
        # adding sheet name
        ws = wb.add_sheet(f'trace {place_to_find_count}')
        row_num = 0
        # setting font style and type
        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        heading = ['Place', 'Date', 'Distinct count', 'Total count', 'Time']
        details = [place_to_find_count, user_date, content['distinct_count'],
                   content['total_count'], message]
        for i in range(len(heading)):
            row_num += 1
            ws.write(row_num, 0, heading[i], font_style)
            ws.write(row_num, 1, str(details[i]), font_style)
            if i == len(heading) - 1:
                row_num += 2
                ws.write(row_num, 0, 'Count data table', font_style)

        details = ['Sr_no', 'Tag_id', 'Name', 'Course', 'Roll number', 'Division', 'Time', 'Status']
        row_num += 1
        for x in range(len(details)):
            ws.write(row_num, x, details[x], font_style)
        row_num += 1
        font_style.font.bold = False
        # entering the student in excel
        for single_line in content['person_list']:
            for sr_no, x in enumerate(single_line, 0):
                ws.write(row_num, sr_no, str(x), font_style)
            row_num += 1

        if content['teacher_list']:
            details = ['Sr_no', 'Tag_id', 'Name', 'Course', 'Practical subject', 'Time', 'Status']
            row_num += 1
            for x in range(len(details)):
                ws.write(row_num, x, details[x], font_style)
            row_num += 1
            font_style.font.bold = False
            # entering the student in excel
            for single_line in content['teacher_list']:
                for sr_no, x in enumerate(single_line, 0):
                    ws.write(row_num, sr_no, str(x), font_style)
                row_num += 1

        wb.save(response)
        return response
    except:
        messages.error(request, 'something went wrong please try again!')
        return redirect('/time_wise-count/')


# this function make excel in accordance to timetable
def timetable_wise_excel(request):
    # setting try/except for the website no to crash by any error occurance
    try:
        # obtaining the get request data
        course = request.GET.get('course')
        user_date = request.GET.get('date')

        # setting the user date (if inputted or not) and interpreting the day for that date
        if user_date:
            user_date = convert_date(user_date)
            split_list_of_date = user_date.split('-')
            day = date(int(split_list_of_date[0]), int(split_list_of_date[1]), int(split_list_of_date[2]))
            day = day.strftime('%A')
        else:
            day = datetime.today().strftime("%A")
            user_date = date.today()

        content = {}
        # getting details from excel for the given course
        cursor = connection.cursor()
        cursor.execute(f'''select distinct(page_timetable.year) from page_timetable where course='{course}';''')
        years = cursor.fetchall()

        iteration = 1
        for year in years:
            cursor = connection.cursor()
            cursor.execute(f'''select page_timetable.start_time,page_timetable.end_time,page_timetable.area,
                        page_timetable."{day}" from page_timetable where course='{course}' and 
                        year='{year[0]}';''')
            year_data = cursor.fetchall()
            ret_values = return_count_value(year_data, user_date)
            content[f'dist_count{iteration}'] = ret_values[0]
            content[f'person_list{iteration}'] = ret_values[1]
            content[f'table{iteration}'] = ret_values[2]
            content[f'batch_time{iteration}'] = ret_values[3]
            content[f'area{iteration}'] = ret_values[4]
            content[f'head{iteration}'] = year[0]
            iteration += 1

        extra_content = {'user_date': str(user_date), 'course': course, 'day': day}
        content.update(extra_content)
        # initializing the excel
        response = HttpResponse(content_type='application/ms-excel')
        # setting filename
        # response['Content-Disposition'] = 'filename=filename.xls'   ##### for viewing the excel online
        # response['Content-Disposition'] = 'attachment; filename=filename.xls'   ##### for downloading the excel
        response['Content-Disposition'] = f'attachment; filename={course}-{date.today()}.xls'
        wb = xlwt.Workbook(encoding='utf-8')
        # adding the sheet name
        ws = wb.add_sheet(f'{course}')

        # setting font style and type
        font_style = xlwt.XFStyle()
        font_style.font.bold = True
        row_num = 1
        ws.write(row_num, 0, 'Showing Timetable Count for', font_style)
        ws.write(row_num, 1, user_date, font_style)
        row_num += 1
        ws.write(row_num, 0, 'Day', font_style)
        ws.write(row_num, 1, day, font_style)
        row_num += 1
        ws.write(row_num, 0, 'Course', font_style)
        ws.write(row_num, 1, course, font_style)
        row_num += 1
        # inputting data into the excel (according to the number of sheets in the excel)
        ws = input_excel_data(row_num, font_style, ws, content, iteration)
        wb.save(response)
        return response
    except:
        messages.error(request, 'something went wrong please try again!')
        return redirect('/timetable_wise-count/')


# this function make pdf for the trace of tag id
def trace_pdf(request):
    try:
        # obtaining the get request dat
        tag_id = request.GET.get('TAG_ID')
        user_date = request.GET.get('DATE')
        table = []

        if tag_id:
            cursor = connection.cursor()
            cursor.execute(f"select * from page_register where page_register.tag_id ='{tag_id}';")
            is_valid_tag = cursor.fetchone()
            tag_origin = 'student'
            if not is_valid_tag:
                cursor = connection.cursor()
                cursor.execute(f"select * from page_teacherregister where page_teacherregister.tag_id ='{tag_id}';")
                is_valid_tag = cursor.fetchone()
                tag_origin = 'teacher'

        # getting the person details for tha tag id (getting list instead of class instance)
        if tag_origin == 'student':
            person = Register.objects.filter(tag_id=tag_id).values_list('tag_id', 'div', 'roll',
                                                                        'name', 'course', 'year')
        else:
            person = TeacherRegister.objects.filter(tag_id=tag_id).values_list('tag_id', 'practical_subject',
                                                                               't_name', 'course')

        person = person[0]
        # getting trace details for the tag id
        cursor = connection.cursor()
        cursor.execute(f"""select area,time,status from page_locationtrack where tag_id_id='{tag_id}' 
                        and date='{user_date}' order by time;""")
        table_data = cursor.fetchall()
        # adding serial number for every trace area
        for sr_no, (area, time, status) in enumerate(table_data, 1):
            table.append([sr_no, area, time, status])

        context = {"table_data": table, "person_data": person, 'date': user_date, 'origin': tag_origin}
        # giving template path
        template_path = 'trace_pdf.html'
        # initializing pdf
        response = HttpResponse(content_type='application/pdf')
        # setting filename
        # response['Content-Disposition'] = 'filename=filename.xls'   ##### for viewing the excel online
        # response['Content-Disposition'] = 'attachment; filename=filename.xls'   ##### for downloading the excel
        response['Content-Disposition'] = f'attachment; filename="{tag_id}-{date.today()}.pdf"'
        template = get_template(template_path)
        html = template.render(context)
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response
    except:
        messages.error(request, 'something went wrong please try again!')
        return redirect('/trace/')


# this function make pdf in accordance to timetable
def timetable_pdf(request):
    try:

        course = request.GET.get('course')
        user_date = request.GET.get('date')
        if user_date:
            user_date = convert_date(user_date)
            split_list_of_date = user_date.split('-')
            day = date(int(split_list_of_date[0]), int(split_list_of_date[1]), int(split_list_of_date[2]))
            day = day.strftime('%A')
        else:
            day = datetime.today().strftime("%A")
            user_date = date.today()

        cursor = connection.cursor()
        cursor.execute(f'''select distinct(page_timetable.year) from page_timetable where course='{course}';''')
        years = cursor.fetchall()

        content = {}
        iteration = 1
        for year in years:
            cursor = connection.cursor()
            cursor.execute(f'''select page_timetable.start_time,page_timetable.end_time,page_timetable.area,
                        page_timetable."{day}" from page_timetable where course='{course}' and 
                        year='{year[0]}';''')
            year_data = cursor.fetchall()
            ret_values = return_count_value(year_data, user_date)
            content[f'dist_count{iteration}'] = ret_values[0]
            content[f'person_list{iteration}'] = ret_values[1]
            content[f'table{iteration}'] = ret_values[2]
            content[f'batch_time{iteration}'] = ret_values[3]
            content[f'area{iteration}'] = ret_values[4]
            content[f'head{iteration}'] = year[0]
            iteration += 1

        extra_content = {'user_date': str(user_date), 'course': course, 'day': day}
        content.update(extra_content)
        template_path = 'timetable_pdf.html'
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{course}-{date.today()}.pdf"'
        template = get_template(template_path)
        html = template.render(content)
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response
    except:
        messages.error(request, 'something went wrong please try again!')
        return redirect('/timetable_wise-count/')


def time_wise_pdf(request):
    try:

        place_to_find_count = request.GET.get('area')
        start_time = request.GET.get("s_t")
        start_minute = request.GET.get("s_m")
        end_time = request.GET.get("e_t")
        end_minute = request.GET.get("e_m")
        user_date = request.GET.get('date')

        if place_to_find_count and not start_time and not end_time:
            message, content = count_for_entire_day(place_to_find_count,
                                                    user_date, start_minute, end_minute)

        if place_to_find_count and start_time and not end_time:
            message, content = count_with_starting_time(start_minute, start_time,
                                                        place_to_find_count, user_date)

        if place_to_find_count and not start_time and end_time:
            message, content = count_with_ending_time(end_minute, end_time, place_to_find_count, user_date)

        if place_to_find_count and start_time and end_time:
            content = count_with_start_end_time(start_minute, end_minute, start_time,
                                                end_time, place_to_find_count, user_date)
            if not start_minute:
                start_minute = 00
            if not end_minute:
                end_minute = 00
            message = f'showing feed for {start_time}:{start_minute} to {end_time}:{end_minute}'

        context = {'Place': place_to_find_count, 'Date': user_date,
                   'Distinct_count': content['distinct_count'], 'Total_count': content['total_count'],
                   'Time': message,
                   'heading': ['Sr_no', 'Tag_id', 'Name', 'Course', 'Roll number', 'Division', 'Time', 'Status'],
                   'data': content['person_list']}

        if content['teacher_list']:
            context['teacher_list'] = content['teacher_list']
            context['t_heading'] = ['Sr_no', 'Tag_id', 'Name', 'Course', 'Practical subject', 'Time', 'Status']

        template_path = 'time_wise_pdf.html'
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{place_to_find_count}-{date.today()}.pdf"'
        template = get_template(template_path)
        html = template.render(context)
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response
    except:
        messages.error(request, 'something went wrong please try again!')
        return redirect('/time_wise-count/')


def what_is_rfid(request):
    return render(request, 'what_is_rfid.html', {'title': 'What is RFID'})


def why_rfid(request):
    return render(request, 'why_rfid.html', {'title': 'Why RFID'})


def how_it_works(request):
    return render(request, 'how_it_works.html', {'title': 'How it works'})
