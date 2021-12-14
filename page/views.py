# the project is meant to get the attendances of students
# the attendance is sent by the raspberry pi using RFID sensor rc522
# the raspberry pi sends api call and the website stores the attendance.

# the module for the django project
from django.shortcuts import render, redirect, HttpResponse
from .models import *
from django.contrib import messages
from django.db import connection
from datetime import date, datetime, timedelta
from .function_list import *
from .serializer import LocationTrackSerializer
from rest_framework.views import APIView
# from .threading import SaveAttendanceThread
from rest_framework.response import Response
from django.contrib.auth import logout as lout
import xlwt
from django.template.loader import get_template
from xhtml2pdf import pisa
from .utils import *
import pandas as pd


# this function redirects to the main page.
def homepage(request):
    # can change the date for thread format is
    # yyyy-mm-dd in string
    # SaveAttendanceThread().start()
    return render(request, "homepage.html", {'title': 'Homepage'})


def logout(request):
    lout(request=request)
    return render(request, "logout.html", {'title': 'Logout'})


class TagApiView(APIView):
    serializer_class = LocationTrackSerializer

    def get(self, request, *args, **kwargs):
        area = request.GET.get('area_')
        tag_id = request.GET.get('tag_')
        tag_date = request.GET.get('date_')
        tag_time = request.GET.get('time_')

        if tag_date:
            obj_id = LocationTrack.objects.filter(tag_id_id=tag_id, date=tag_date).order_by('-time')
        else:
            obj_id = LocationTrack.objects.filter(tag_id_id=tag_id, date=date.today()).order_by('-time')
        data = LocationTrackSerializer(obj_id, many=True)

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

        if not tag_id or not area or not tag:
            return Response(data.data)
        if area and tag:
            cursor = connection.cursor()
            if tag_date:
                previous_visited_date = (tag_date,)
            else:
                cursor.execute(f"select max(date) from page_locationtrack where tag_id_id='{tag_id}';")
                previous_visited_date = cursor.fetchone()
            # checking the IN/OUT status for the student

            if not tag_date:
                if previous_visited_date[0] != date.today():
                    # if new day, then status should be IN
                    status = 'IN'
                else:
                    # if already has entry in database for the day
                    cursor = connection.cursor()
                    if not tag_date:
                        cursor.execute(f"""select area, status from page_locationtrack where tag_id_id = '{tag_id}'
                            and time=(select max(time) from page_locationtrack where tag_id_id = '{tag_id}'
                            and date=(select max(date) from page_locationtrack where tag_id_id='{tag_id}'));""")
                        previous_visited_place, status = cursor.fetchone()
                    else:
                        cursor.execute(f"""select area, status from page_locationtrack where tag_id_id = '{tag_id}'
                                            and time=(select max(time) from page_locationtrack where tag_id_id = '{tag_id}'
                                            and date=(select max(date) from page_locationtrack where tag_id_id='{tag_id}'
                                            and date='{tag_date}'));""")
                        previous_visited_place, status = cursor.fetchone()

                    if previous_visited_place == area and status == 'IN':
                        status = 'OUT'
                    elif previous_visited_place == area and status == 'OUT':
                        status = 'IN'
                    else:
                        status = 'IN'
            else:
                cursor = connection.cursor()
                cursor.execute(f"""select * from page_locationtrack where tag_id_id='{tag_id}' and
                                date='{tag_date}' and time < '{tag_time}' order by time;""")
                previous_tags = cursor.fetchall()

                cursor.execute(f"""select * from page_locationtrack where tag_id_id='{tag_id}' and
                                date='{tag_date}' and time > '{tag_time}' order by time;""")
                after_tags = cursor.fetchall()

                if previous_tags:
                    id_, record_area, record_tag, record_date, record_time, record_status = previous_tags[-1]
                    if record_area == area:
                        if record_status == 'IN':
                            status = 'OUT'
                        else:
                            status = "IN"
                    else:
                        status = 'IN'
                else:
                    status = 'IN'

                current_status = status
                status_dict = {'IN': 'OUT', 'OUT': 'IN'}
                if after_tags:
                    for record in after_tags:
                        id_, record_area, record_tag, record_date, record_time, record_status = record
                        if record_area != area:
                            break
                        current_row = LocationTrack.objects.get(id=id_)
                        current_row.status = status_dict[current_status]
                        current_row.save()
                        current_status = status_dict[current_status]

        # saving the responses to database
        entry = LocationTrack()
        entry.area = area
        entry.tag_id_id = tag_id
        entry.status = status
        if tag_time and tag_date:
            entry.time = tag_time
            entry.date = tag_date
        entry.save()

        return Response(data.data)


def analyse_attendance(request):
    content = {'course': {}, 'title': 'Analyse', 'date_list': get_date()}
    timetable_df = pd.DataFrame(Timetable.objects.all().values())

    start_date = request.GET.get('DATE1')
    end_date = request.GET.get('DATE2')
    course = request.GET.get('course')
    year = request.GET.get('year')
    student_roll_number = request.GET.get('std_roll')
    if course:
        content['is_course'] = course
    if year:
        content['is_year'] = year

    is_bar_graph = False
    is_batch_graph = False

    student = pd.DataFrame(Register.objects.all().values()).drop(['course', 'year'], axis=1)
    timetable = timetable_df.drop(
        ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'area'],
        axis=1)
    attendance = pd.DataFrame(AttendanceRecord.objects.all().values()).drop(['id'], axis=1).rename(
        columns={'student_id': 'tag_id', 'attendance_id': 'id'})

    df1 = pd.merge(attendance, student, on='tag_id')
    df2 = pd.merge(df1, timetable, on='id').drop(['id'], axis=1)

    compare_graphs = {}
    # ---------------------------------------------------------------
    if student_roll_number:
        is_bar_graph = True

        distinct_batch = df2[(df2['course'] == course) & (df2['year'] == year) &
                             (df2['roll'] == int(student_roll_number))].drop_duplicates(
            subset='batch')['batch'].values.tolist()

        if start_date and end_date:
            start_date = date(*list(map(int, start_date.split('-'))))
            end_date = date(*list(map(int, end_date.split('-'))))
            for batch in distinct_batch:
                df3 = df2.loc[(df2['date'] <= start_date) & (df2['date'] >= end_date) & (df2['batch'] == batch) &
                              (df2['course'] == course) & (df2['year'] == year) &
                              (df2['roll'] == int(student_roll_number))]

                dist_counts = df3.sort_values(
                    'date').groupby(['roll', 'date']).roll.nunique().to_dict()
                dist_dates = df3['date'].unique().tolist()
                compare_graphs[f'{batch}-{student_roll_number}'] = comparision_plot(dist_counts, dist_dates,
                                                                                    f'{course}-{year}-{batch}',
                                                                                    is_bar_graph)
        elif start_date:
            start_date = date(*list(map(int, start_date.split('-'))))
            for batch in distinct_batch:
                df3 = df2.loc[(df2['date'] <= start_date) & (df2['course'] == course) & (df2['year'] == year)
                              & (df2['roll'] == int(student_roll_number)) & (df2['batch'] == batch)]
                dist_counts = df3.sort_values(
                    'date').groupby(['roll', 'date']).roll.nunique().to_dict()
                dist_dates = df3['date'].unique().tolist()
                compare_graphs[f'{batch}-{student_roll_number}'] = comparision_plot(dist_counts, dist_dates,
                                                                                    f'{course}-{year}-{batch}',
                                                                                    is_bar_graph)
        else:
            for batch in distinct_batch:
                df3 = df2.loc[(df2['course'] == course) & (df2['year'] == year) &
                              (df2['roll'] == int(student_roll_number)) & (df2['batch'] == batch)]

                dist_counts = df3.sort_values(
                    'date').groupby(['roll', 'date']).roll.nunique().to_dict()
                dist_dates = df3['date'].unique().tolist()
                compare_graphs[f'{batch}-{student_roll_number}'] = comparision_plot(dist_counts, dist_dates,
                                                                                    f'{course}-{year}-{batch}',
                                                                                    is_bar_graph)
        content['compare_graph'] = compare_graphs

        return render(request, 'analyse.html', content)

    # -------------------------------------------------------------
    if course and year:
        is_batch_graph = True
        if start_date and end_date:
            content['start_date'] = start_date
            content['end_date'] = end_date

            start_date = date(*list(map(int, start_date.split('-'))))
            end_date = date(*list(map(int, end_date.split('-'))))
            df3 = df2.loc[(df2['date'] <= start_date) & (df2['date'] >= end_date) &
                          (df2['course'] == course) & (df2['year'] == year)]
        elif start_date and not end_date:
            content['start_date'] = start_date
            start_date = date(*list(map(int, start_date.split('-'))))
            df3 = df2.loc[(df2['course'] == course) & (df2['year'] == year) & (df2['date'] == start_date)]
            is_bar_graph = True
        else:
            df3 = df2[(df2['course'] == course) & (df2['year'] == year)]

        distinct_counts = df3.sort_values(['date']).groupby(['batch', 'date']).roll.nunique().to_dict()
        distinct_dates = df3['date'].unique().tolist()

    elif course:
        if start_date and end_date:
            content['start_date'] = start_date
            content['end_date'] = end_date
            start_date = date(*list(map(int, start_date.split('-'))))
            end_date = date(*list(map(int, end_date.split('-'))))

            df3 = df2.loc[(df2['course'] == course) & (df2['date'] <= start_date) & (df2['date'] >= end_date)]
        elif start_date:
            start_date = date(*list(map(int, start_date.split('-'))))
            df3 = df2.loc[(df2['course'] == course) & (df2['date'] == start_date)]
            is_bar_graph = True
        else:
            df3 = df2[df2['course'] == course]

        distinct_counts = df3.sort_values(['date']).groupby(['year', 'batch', 'date']).roll.nunique().to_dict()
        distinct_dates = df3['date'].unique().tolist()

    else:
        if start_date and end_date:
            content['start_date'] = start_date
            content['end_date'] = end_date

            start_date = date(*list(map(int, start_date.split('-'))))
            end_date = date(*list(map(int, end_date.split('-'))))
            df3 = df2.loc[(df2['date'] <= start_date) & (df2['date'] >= end_date)]
        elif start_date and not end_date:
            content['start_date'] = start_date
            start_date = date(*list(map(int, start_date.split('-'))))
            df3 = df2.loc[df2['date'] == start_date]
            is_bar_graph = True
        else:
            df3 = df2
        distinct_counts = df3.sort_values(['date']).groupby(['course', 'year', 'date']).roll.nunique().to_dict()
        distinct_dates = df3['date'].unique().tolist()

    content['main_graph'] = combine_plot(distinct_counts, distinct_dates, is_bar_graph, is_batch_graph)

    # -----------------------------------------------------------------------
    if course and year:
        distinct_batch = df2[(df2['course'] == course) & (df2['year'] == year)].drop_duplicates(
            subset='batch')['batch'].values.tolist()

        if start_date and end_date:
            for batch in distinct_batch:
                dist_counts = df2.loc[(df2['course'] == course) & (df2['date'] <= start_date) &
                                      (df2['date'] >= end_date) & (df2['year'] == year) & (df2['batch'] == batch)
                                      ].sort_values(
                    'date').groupby(['batch', 'date']).roll.nunique().to_dict()
                dist_dates = df2.loc[(df2['course'] == course) & (df2['date'] <= start_date)
                                     & (df2['date'] >= end_date) & (df2['year'] == year) & (df2['batch'] == batch)][
                    'date'].unique().tolist()
                compare_graphs[batch] = comparision_plot(dist_counts, dist_dates, f'{course}-{year}-{batch}',
                                                         is_bar_graph)
        elif start_date and not end_date:
            for batch in distinct_batch:
                dist_counts = df2.loc[(df2['course'] == course) & (df2['date'] == start_date)
                                      & (df2['year'] == year) & (df2['batch'] == batch)].sort_values(
                    'date').groupby(['batch', 'date']).roll.nunique().to_dict()
                dist_dates = df2.loc[(df2['course'] == course) & (df2['date'] == start_date)
                                     & (df2['year'] == year) & (df2['batch'] == batch)]['date'].unique().tolist()
                is_bar_graph = True
                compare_graphs[batch] = comparision_plot(dist_counts, dist_dates, f'{course}-{year}-{batch}',
                                                         is_bar_graph)
        else:
            for batch in distinct_batch:
                dist_counts = df2.loc[(df2['course'] == course) & (df2['year'] == year) & (df2['batch'] == batch)
                                      ].sort_values(
                    ['date']).groupby(['batch', 'date']).roll.nunique().to_dict()
                dist_dates = df2.loc[(df2['course'] == course) & (df2['year'] == year) & (df2['batch'] == batch)
                                     ]['date'].unique().tolist()
                compare_graphs[batch] = comparision_plot(dist_counts, dist_dates, f'{course}-{year}-{batch}',
                                                         is_bar_graph)

    elif course:
        distinct_year = df2[df2['course'] == course].drop_duplicates(subset='year')['year'].values.tolist()

        if start_date and end_date:
            for year in distinct_year:
                dist_counts = df2.loc[(df2['course'] == course) & (df2['date'] <= start_date) &
                                      (df2['date'] >= end_date) & (df2['year'] == year)].sort_values(
                    'date').groupby(['batch', 'date']).roll.nunique().to_dict()
                dist_dates = df2.loc[(df2['course'] == course) & (df2['date'] <= start_date)
                                     & (df2['date'] >= end_date) & (df2['year'] == year)][
                    'date'].unique().tolist()
                compare_graphs[year] = comparision_plot(dist_counts, dist_dates, course, is_bar_graph)
        elif start_date and not end_date:
            for year in distinct_year:
                dist_counts = df2.loc[(df2['course'] == course) & (df2['date'] == start_date)
                                      & (df2['year'] == year)].sort_values(
                    'date').groupby(['batch', 'date']).roll.nunique().to_dict()
                dist_dates = df2.loc[(df2['course'] == course) & (df2['date'] == start_date)
                                     & (df2['year'] == year)]['date'].unique().tolist()
                is_bar_graph = True
                compare_graphs[year] = comparision_plot(dist_counts, dist_dates, course, is_bar_graph)
        else:
            for year in distinct_year:
                dist_counts = df2.loc[(df2['course'] == course) & (df2['year'] == year)].sort_values(
                    ['date']).groupby(['batch', 'date']).roll.nunique().to_dict()
                dist_dates = df2.loc[(df2['course'] == course) & (df2['year'] == year)]['date'].unique().tolist()
                compare_graphs[year] = comparision_plot(dist_counts, dist_dates, f'{course}-{year}', is_bar_graph)

    else:
        distinct_courses = df2.drop_duplicates(subset='course')['course'].values.tolist()
        if start_date and end_date:
            for course in distinct_courses:
                dist_counts = df2.loc[(df2['course'] == course) & (df2['date'] <= start_date) & (df2['date'] >= end_date
                                                                                                 )].sort_values(
                    ['date']).groupby(['year', 'date']).roll.nunique().to_dict()
                dist_dates = df2.loc[(df2['course'] == course) & (df2['date'] <= start_date) & (df2['date'] >= end_date
                                                                                                )][
                    'date'].unique().tolist()
                compare_graphs[course] = comparision_plot(dist_counts, dist_dates, course, is_bar_graph)
        elif start_date and not end_date:
            for course in distinct_courses:
                dist_counts = df2.loc[(df2['course'] == course) & (df2['date'] == start_date)].sort_values(
                    ['date']).groupby(['year', 'date']).roll.nunique().to_dict()
                dist_dates = df2.loc[(df2['course'] == course) & (df2['date'] == start_date)]['date'].unique().tolist()
                is_bar_graph = True
                compare_graphs[course] = comparision_plot(dist_counts, dist_dates, course, is_bar_graph)
        else:
            for course in distinct_courses:
                dist_counts = df2.loc[df2['course'] == course].sort_values(
                    ['date']).groupby(['year', 'date']).roll.nunique().to_dict()
                dist_dates = df2.loc[df2['course'] == course]['date'].unique().tolist()
                compare_graphs[course] = comparision_plot(dist_counts, dist_dates, course, is_bar_graph)

    content['compare_graph'] = compare_graphs
    return render(request, 'analyse.html', content)


def view_timetable(request):
    content = {'head': ['COURSE', 'YEAR', 'PLACE', 'START TIME', 'END TIME',
                        'MON', 'TUE', 'WED', 'THUR', 'FRI', 'SAT', 'SUN'],
               'course': {}, 'title': "View TimeTable"}
    # cursor = connection.cursor()
    # cursor.execute('select distinct(page_timetable.course) from page_timetable;')
    # courses = cursor.fetchall()
    timetable_df = pd.DataFrame(Timetable.objects.all().values())
    courses = timetable_df['course'].unique().tolist()

    if courses:
        for course in courses:
            '''cursor.execute(fselect page_timetable.course, page_timetable.year,
                                page_timetable.area, page_timetable.start_time, page_timetable.end_time,
                                page_timetable."Monday",page_timetable."Tuesday",page_timetable.'Wednesday',
                                page_timetable.'Thursday',page_timetable.'Friday',page_timetable.'Saturday',
                                page_timetable.'Sunday' from page_timetable 
                                where page_timetable.course = '{course[0]}'
                                order by page_timetable.year ; )'''
            data = timetable_df.loc[(timetable_df['course'] == course)].sort_values('year')[['course',
                                'year', 'area', 'start_time', 'end_time', 'Monday', 'Tuesday',
                                'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']]

            content['course'][f'{course}'] = data.rename({'Monday': 'Mon', 'Tuesday': "Tue", "Wednesday": "Wed",
                                                          'Thursday': "Thur",
                         'Friday': "Fri", 'Saturday': "Sat", 'Sunday': "Sun", 'start_time': "StartTime",
                         'end_time': "EndTime"}, axis=1).to_html(classes="table table-hover", index=False)

    else:
        messages.error(request, 'No timetable to show!')
    return render(request, 'view.html', content)


def save_attendance(request):
    content = {'date': get_date(), 'title': 'Save Attendance', 'checked_list': []}

    timetable_df = pd.DataFrame(Timetable.objects.all().values())
    if timetable_df.empty:
        messages.error(request, "Currently No TIMETABLE present!!!")
        return render(request, 'save_attendance.html', content)
    else:
        no_of_years = timetable_df.drop(['Monday', 'Tuesday', 'Wednesday',
                                     'Thursday', 'Friday', 'Saturday', 'Sunday',
                                     'start_time', 'end_time', 'id'], axis=1).groupby(
                                    ['course']).year.unique()
    sample_dict = {}

    for course, year_array in no_of_years.iteritems():
        sample_dict[course] = str(year_array.tolist())[1:-1]

    # no_of_years = no_of_years.to_dict()

    # content['year_id'] = no_of_years
    content['year_id'] = sample_dict
    year_index = {'one': 'FY', 'two': 'SY', 'three': 'TY'}
    day_index = {'Monday': 6, 'Tuesday': 7, 'Wednesday': 8, 'Thursday': 9, 'Friday': 10, 'Saturday': 11, 'Sunday': 12}

    if request.method == 'GET':
        course_for_attendance = request.GET.get('course')
        year_of_attendance = request.GET.get('year')
        date_of_attendance = request.GET.get('date')
        area_of_attendance = request.GET.get('area')

        if year_of_attendance:
            year_of_attendance = year_of_attendance.replace(" ", "")

        if not date_of_attendance:
            date_of_attendance = date.today()

        split_list_of_date = str(date_of_attendance).split('-')
        day = date(int(split_list_of_date[0]), int(split_list_of_date[1]), int(split_list_of_date[2]))
        day = day.strftime('%A')

        if course_for_attendance and area_of_attendance:
            attendance_record = timetable_df.loc[(timetable_df['course'] == course_for_attendance) &
                                                 (timetable_df['year'] == year_of_attendance)].values.tolist()

            if len(attendance_record) == 1:
                multiple_batches = False
                attendance_record = attendance_record[0]
                start_time = datetime.strptime(str(attendance_record[4]), '%H:%M:%S')
                end_time = datetime.strptime(str(attendance_record[5]), '%H:%M:%S')

                start_time = (start_time - timedelta(minutes=10)).time()
                end_time = (end_time + timedelta(minutes=10)).time()
            else:
                multiple_batches = True
                batches_list = []
                for record in attendance_record:
                    start_time = datetime.strptime(str(record[4]), '%H:%M:%S')
                    end_time = datetime.strptime(str(record[5]), '%H:%M:%S')
                    start_time = (start_time - timedelta(minutes=10)).time()
                    end_time = (end_time + timedelta(minutes=10)).time()

                    batches_list.append([record[0], record[day_index[day]], str(start_time), str(end_time)])

            students_details = pd.DataFrame(Register.objects.all().values())

            if not multiple_batches:
                students_table = pd.DataFrame(
                    LocationTrack.objects.filter(area=area_of_attendance, date=date_of_attendance,
                                                 status='IN', time__gte=start_time,
                                                 time__lte=end_time).order_by(
                        'time').values()).rename(columns={'tag_id_id': 'tag_id'})

                if students_table.empty:
                    messages.error(request, 'No records')
                    return render(request, 'save_attendance.html', content)

                students = pd.merge(students_table, students_details, on='tag_id').drop_duplicates("tag_id",
                                                                                    keep='last').drop(
                    ['area', 'date', 'status'], axis=1)
                students['time'] = students['time'].astype(str)

                timetable_id = Timetable.objects.filter(course=course_for_attendance, year=year_of_attendance
                                                        ).values('id')[0]['id']
                # ---------------------------------------------
                batch = Timetable.objects.filter(id=int(timetable_id)).values(day)[0][day]
                data = AttendanceRecord.objects.filter(attendance=timetable_id,
                                                       date=date_of_attendance, batch=batch).values('student')
                students_tag_list = []
                for _ in data:
                    for key, item in _.items():
                        students_tag_list.append(item)
                # ----------------------------------------------
                content['batch'] = [attendance_record[day_index[day]], str(start_time), str(end_time)]
                if any(students_tag_list):
                    content['checked'] = students_tag_list
                else:
                    content['checked'] = str([0])
            else:
                start_time_list, end_time_list = [], []
                for record in batches_list:
                    start_time_list.append(record[2])
                    end_time_list.append(record[3])
                start_time = min(start_time_list)
                end_time = max(end_time_list)
                students_table = pd.DataFrame(
                    LocationTrack.objects.filter(area=area_of_attendance, date=date_of_attendance,
                                                 status='IN', time__gte=start_time,
                                                 time__lte=end_time).order_by(
                        'time').values()).rename(columns={'tag_id_id': 'tag_id'})

                if students_table.empty:
                    messages.error(request, 'No records')
                    return render(request, 'save_attendance.html', content)

                # students = pd.merge(students_table, students_details, on='tag_id').drop_duplicates("tag_id",
                #                                                                         keep='last').drop(
                students = pd.merge(students_table, students_details, on='tag_id').drop(
                    ['area', 'date', 'status'], axis=1)
                students['time'] = students['time'].astype(str)

                content['batch_list'] = batches_list
                # ---------------------------------------------
                students_tag_list = []
                for data in batches_list:
                    id_, batch, s_time, e_time = data
                    data = AttendanceRecord.objects.filter(attendance=id_,
                                                           date=date_of_attendance, batch=batch).values('student')
                    list_ = []
                    for _ in data:
                        for key, item in _.items():
                            list_.append(int(item))
                    if any(list_):
                        students_tag_list.append(list_)
                    else:
                        students_tag_list.append([0])
                # ----------------------------------------------
                content['checked_list'] = students_tag_list
            extra_content = {'table': students[
                ['tag_id', 'name', 'div', 'roll', 'course', 'year', 'time']].values.tolist(),
                             'area': area_of_attendance, 'user_date': str(date_of_attendance),
                             'course': course_for_attendance,
                             'year': year_of_attendance}

            if not multiple_batches:
                content['t_id'] = timetable_id

            content.update(extra_content)

        return render(request, 'save_attendance.html', content)

    elif request.method == 'POST':
        timetable_id = request.POST.get('t_id')
        std_records = request.POST.getlist('std_records')
        user_date = request.POST.get('date')
        area = request.POST.get('area')
        checked_tags = request.POST.get('checked_tags')

        std_records = list(map(lambda x: int(x), std_records))
        if checked_tags:
            checked_tags = list(map(lambda x: int(x.replace("'", "")), checked_tags[1:-1].split(',')))
        else:
            checked_tags = []
        split_list_of_date = user_date.split('-')
        day = date(int(split_list_of_date[0]), int(split_list_of_date[1]), int(split_list_of_date[2]))
        day = day.strftime('%A')

        batch = Timetable.objects.filter(id=int(timetable_id)).values(day)[0][day]
        content['data'] = std_records

        # -----------------------------------------------------------
        removed_tags = []
        for tag in checked_tags:
            if tag in std_records or tag == 0:
                continue
            removed_tags.append(tag)

        # deleting the unchecked records
        for tag in removed_tags:
            AttendanceRecord.objects.filter(attendance=timetable_id, student=tag, date=user_date, batch=batch).delete()
        # ----------------------------------------

        count = 0
        for student in std_records:
            # student_tag = LocationTrack.objects.filter(id=student).values('tag_id_id')[0]['tag_id_id']
            if AttendanceRecord.objects.filter(attendance=timetable_id, student=student, date=user_date,
                                               batch=batch).values():
                continue
            attendance = AttendanceRecord()
            attendance.student_id = student
            attendance.attendance_id = timetable_id
            attendance.date = user_date
            attendance.day = day
            attendance.batch = batch
            attendance.area = area
            attendance.save()
            count += 1

        content['s_count'] = str(count)
        content['d_count'] = str(len(removed_tags))
        return render(request, 'save_attendance.html', content)


def attendance_excel_pdf(request, method=None):
    student = pd.DataFrame(Register.objects.all().values()).drop(['course', 'year'], axis=1)
    timetable = pd.DataFrame(Timetable.objects.all().values()).drop(
        ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'area'],
        axis=1)
    attendance = pd.DataFrame(AttendanceRecord.objects.all().values()).drop(['id'], axis=1).rename(
        columns={'student_id': 'tag_id', 'attendance_id': 'id'})

    start_date = request.GET.get('date')
    end_date = request.GET.get('end_date')

    today = start_date.split('-')
    previous_date = end_date.split('-')
    today = date(int(today[0]), int(today[1]), int(today[2]))
    previous_date = date(int(previous_date[0]), int(previous_date[1]), int(previous_date[2]))

    content = {'courses_head': {}, 'courses': {}, 'today': str(today),
               'last_date': str(previous_date)}

    if method == '1':
        try:
            df1 = pd.merge(attendance, student, on='tag_id')
            df2 = pd.merge(df1, timetable, on='id').drop(['id'], axis=1)
            df2['date'] = pd.to_datetime(df2['date'])
            mask = (df2['date'] >= str(previous_date)) & (df2['date'] <= str(today))
            df2 = df2.loc[mask]
            df_by_course = df2.groupby(['course'])

            for key, item in df_by_course:
                content['courses'][f'{key}'] = {}
                # df_by_year = item.groupby(['year'])
                data = item.reset_index(drop=True).sort_values(
                    ['date']).drop('day', axis=1)[['tag_id', 'name', 'div', 'roll', 'course', 'year', 'area', 'batch',
                                                   'start_time', 'end_time', 'batch', 'date']]
                content['courses_head'][f'{key}'] = data.columns
                content['courses'][f'{key}'] = data.values.tolist()

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

                for col, head in enumerate(content['courses_head'][f'{course}'], start=2):
                    ws.write(row_num, col, f'{str(head)}', font_style)
                row_num += 1
                for records in data:
                    for col, values in enumerate(records, start=2):
                        ws.write(row_num, col, f'{str(values)}', font_style)
                    row_num += 1
                row_num += 3
            wb.save(response)
            return response
        except:
            messages.error(request, 'something went wrong please try again!')
            return redirect('/attendance/')
    elif method == '2':
        try:
            df1 = pd.merge(attendance, student, on='tag_id')
            df2 = pd.merge(df1, timetable, on='id').drop(['id'], axis=1)
            df2['date'] = pd.to_datetime(df2['date'])
            mask = (df2['date'] >= str(previous_date)) & (df2['date'] <= str(today))
            df2 = df2.loc[mask]
            df_by_course = df2.groupby(['course'])

            for key, item in df_by_course:
                content['courses'][f'{key}'] = {}
                # df_by_year = item.groupby(['year'])
                data = item.reset_index(drop=True).sort_values(
                    ['date']).drop('day', axis=1)[['tag_id', 'name', 'div', 'roll', 'course', 'year', 'area', 'batch',
                                                   'start_time', 'end_time', 'batch', 'date']]
                content['courses'][f'{key}'] = data.to_html(classes="table table-hover", index=False)

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
        except:
            messages.error(request, 'something went wrong please try again!')
            return redirect('/attendance/')


def attendance_data(requests):
    if requests.method == 'GET':

        student = pd.DataFrame(Register.objects.all().values()).drop(['course', 'year'], axis=1)
        timetable = pd.DataFrame(Timetable.objects.all().values()).drop(
            ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'area'],
            axis=1)
        attendance = pd.DataFrame(AttendanceRecord.objects.all().values()).drop(['id'], axis=1).rename(
            columns={'student_id': 'tag_id', 'attendance_id': 'id'})

        start_date = requests.GET.get('START_DATE')
        end_date = requests.GET.get('END_DATE')

        if not start_date and not end_date:
            if not start_date:
                today = date.today()
            else:
                user_date = start_date.split('-')
                today = date(int(user_date[0]), int(user_date[1]), int(user_date[2]))

            previous_date = today.replace(day=1)
            if today == previous_date:
                previous_date = str(previous_date).split('-')
                if int(previous_date[1]) == 1:
                    previous_month = 12
                else:
                    previous_month = int(previous_date[1]) - 1
                previous_date = date(int(previous_date[0]), int(previous_month), int(previous_date[2]))
        elif start_date and (not end_date):
            messages.error(requests, 'Please select the END DATE')
            return render(requests, 'weekly.html', {'date': get_date(), 'title': 'Attendance records'})
        elif end_date and (not start_date):
            messages.error(requests, 'Please select the START DATE')
            return render(requests, 'weekly.html', {'date': get_date(), 'title': 'Attendance records'})
        else:
            today = start_date
            previous_date = end_date

        content = {'courses': {}, 'today': str(today),
                   'last_date': str(previous_date),
                   'title': 'Attendance records'}

        df1 = pd.merge(attendance, student, on='tag_id')
        df2 = pd.merge(df1, timetable, on='id').drop(['id'], axis=1)

        df2['date'] = pd.to_datetime(df2['date'])
        mask = (df2['date'] >= str(previous_date)) & (df2['date'] <= str(today))
        df2 = df2.loc[mask]

        df_by_course = df2.groupby(['course'])

        for key, item in df_by_course:
            content['courses'][f'{key}'] = {}
            # df_by_year = item.groupby(['year'])

            data = item.reset_index(drop=True).sort_values(
                ['date']).drop('day', axis=1)[['tag_id', 'name', 'div', 'roll', 'course', 'year', 'area', 'batch',
                                               'start_time', 'end_time', 'batch', 'date']]
            content['courses'][f'{key}'] = data.to_html(classes="table table-hover", index=False)

        content['date'] = get_date()
        return render(requests, 'weekly.html', content)
    return render(requests, 'weekly.html', {'date': get_date(), 'title': 'Monthly data'})


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

    if request.method == 'GET':
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
                             'date': date_list, 'title': 'Time-Count', 'message': message}
            # adding 2 dict
            content.update(extra_content)
            # messages.success(request, message)
            return render(request, 'count.html', content)

        # getting content for particular area with starting time
        if place_to_find_count and start_time and not end_time:
            # getting content :- function_list.py
            message, content = count_with_starting_time(start_minute, start_time,
                                                        place_to_find_count, user_date)
            # adding extra content (required for excel/pdf download)
            extra_content = {'area': place_to_find_count, 'start_time': start_time, 'start_minute': start_minute,
                             'end_time': end_time, 'end_minute': end_minute, 'user_date': str(user_date),
                             'date': date_list, 'title': 'Time-Count', 'message': message}
            # adding 2 dict
            content.update(extra_content)
            # messages.success(request, message)
            return render(request, 'count.html', content)

        # getting content for particular area with ending time
        if place_to_find_count and not start_time and end_time:
            # getting content  :- function_list.py
            message, content = count_with_ending_time(end_minute, end_time, place_to_find_count, user_date)
            # adding extra content (required for excel/pdf download)
            extra_content = {'area': place_to_find_count, 'start_time': start_time, 'start_minute': start_minute,
                             'end_time': end_time, 'end_minute': end_minute, 'user_date': str(user_date),
                             'date': date_list, 'title': 'Time-Count', 'message': message}
            # adding 2 dict
            content.update(extra_content)
            # messages.success(request, message)
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
            content['message'] = f'showing feed for {start_time}:{start_minute} to {end_time}:{end_minute}'
            # messages.success(request, message)

            return render(request, 'count.html', content)
    return render(request, 'count.html', {"date": date_list, 'title': 'Time-Count'})


# this function redirects the time_wise/timetable_wise count html page
# currently not needed -> doesnt exist now
def count_person(request):
    return render(request, 'count_selection.html')


# this above function is not in use


# this function make student count in accordance to the timetable
def timetable_wise_count(request):
    # getting distinct date from database
    timetable_df = pd.DataFrame(AttendanceRecord.objects.all().values())
    if timetable_df.empty:
        messages.warning(request, "No attendances!!!!")
        return render(request, 'timetable.html', {})
    else:
        dates = timetable_df.sort_values('date', ascending=False)['date'].unique()
        date_list = list(map(lambda x: str(x), dates))

    timetable_df = pd.DataFrame(Timetable.objects.all().values())

    no_of_years = timetable_df.drop(['Monday', 'Tuesday', 'Wednesday',
                                     'Thursday', 'Friday', 'Saturday', 'Sunday',
                                     'start_time', 'end_time', 'id'], axis=1).groupby(
        ['course']).year.unique()
    sample_dict = {}

    for course, year_array in no_of_years.iteritems():
        sample_dict[course] = str(year_array.tolist())[1:-1]

    no_of_years = sample_dict

    content = {'date': date_list, 'title': 'TimeTable-Count', 'year_id': no_of_years}
    year_index = {'one': 'FY', 'two': 'SY', 'three': 'TY'}

    if request.method == 'GET':
        # getting html variables
        course = request.GET.get('course')
        year = request.GET.get('year')
        user_date = request.GET.get('DATE')

        if year:
            year = year.replace(" ", "")

        # giving appropriate message to select
        if (not course or not year) and user_date:
            messages.error(request, "please select Course")
            return render(request, 'timetable.html', content)

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
        if course and year:
            timetable_id = timetable_df.loc[(timetable_df['course'] == course) &
                                            (timetable_df['year'] == year)]['id'].values.tolist()

            attendance_record = pd.DataFrame(AttendanceRecord.objects.all().values()).drop('id', axis=1).rename(
                columns={'attendance_id': 'id', 'student_id': 'tag_id'})
            attendance_record['date'] = pd.to_datetime(attendance_record['date'])

            student_attendance = attendance_record.loc[attendance_record['id'].isin(timetable_id)]
            student_attendance = student_attendance[student_attendance['date'] == str(user_date)]

            if student_attendance.empty:
                messages.error(request, 'No Records!!!')
                return render(request, 'timetable.html', content)

            student_details = pd.DataFrame(Register.objects.all().values())
            student_attendance = pd.merge(student_details, student_attendance, on='tag_id')
            group_by_student_attendance = student_attendance.groupby('id')
            content['table'] = []
            for id_, data in group_by_student_attendance:
                content['table'].append(data.reset_index(drop=True).sort_values(
                    ['date']).drop(['id', 'date', 'day'], axis=1).to_html(classes="table table-hover", index=False))
            extra_content = {'date': date_list, 'user_date': str(user_date), 'course': course, 'day': day,
                             'title': 'TimeTable-Count', 'year': year}
            # adding 2 dict
            content.update(extra_content)
            messages.success(request, f'showing Attendance for {user_date}')

            return render(request, 'timetable.html', content)
    return render(request, 'timetable.html', content)


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
    # setting try/except for the website to not to crash by any error occurance
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

        details = ['Sr_no', 'Tag_id', 'Name', 'Course', 'Roll number', 'Division', 'In-Time', 'Out-Time']
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
            details = ['Sr_no', 'Tag_id', 'Name', 'Course', 'Practical subject', 'In-Time', 'Out-Time']
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
        timetable_df = pd.DataFrame(Timetable.objects.all().values())

        # obtaining the get request data
        course = request.GET.get('course')
        user_date = request.GET.get('date')
        year = request.GET.get('year')

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

        extra_content = {'user_date': str(user_date), 'course': course, 'day': day, 'year': year}
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
        ws.write(row_num, 0, 'Year', font_style)
        ws.write(row_num, 1, year, font_style)
        row_num += 1
        # ======================================================================
        timetable_id = timetable_df.loc[(timetable_df['course'] == course) &
                                        (timetable_df['year'] == year)]['id'].values.tolist()

        attendance_record = pd.DataFrame(AttendanceRecord.objects.all().values()).drop('id', axis=1).rename(
            columns={'attendance_id': 'id', 'student_id': 'tag_id'})
        attendance_record['date'] = pd.to_datetime(attendance_record['date'])

        student_attendance = attendance_record.loc[attendance_record['id'].isin(timetable_id)]
        student_attendance = student_attendance[student_attendance['date'] == user_date]

        student_details = pd.DataFrame(Register.objects.all().values())
        student_attendance = pd.merge(student_details, student_attendance, on='tag_id')
        group_by_student_attendance = student_attendance.groupby('id')
        content['table'] = []
        for id_, data in group_by_student_attendance:
            table = data.reset_index(drop=True).sort_values(
                ['date']).drop(['id', 'date', 'day'], axis=1)
            cols = table.columns
            ws, row_num = input_excel_data(row_num, font_style, ws, table.values.tolist(), cols)
            # =============================================================
            # setting font style and type
            # inputting data into the excel (according to the number of sheets in the excel)
            # ws = input_excel_data(row_num, font_style, ws, content, iteration)
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
        timetable_df = pd.DataFrame(Timetable.objects.all().values())

        content = {}
        course = request.GET.get('course')
        user_date = request.GET.get('date')
        year = request.GET.get('year')
        if user_date:
            user_date = convert_date(user_date)
            split_list_of_date = user_date.split('-')
            day = date(int(split_list_of_date[0]), int(split_list_of_date[1]), int(split_list_of_date[2]))
            day = day.strftime('%A')
        else:
            day = datetime.today().strftime("%A")
            user_date = date.today()
        # ============================================================
        if course and year:
            timetable_id = timetable_df.loc[(timetable_df['course'] == course) &
                                            (timetable_df['year'] == year)]['id'].values.tolist()

            attendance_record = pd.DataFrame(AttendanceRecord.objects.all().values()).drop('id', axis=1).rename(
                columns={'attendance_id': 'id', 'student_id': 'tag_id'})
            attendance_record['date'] = pd.to_datetime(attendance_record['date'])

            student_attendance = attendance_record.loc[attendance_record['id'].isin(timetable_id)]
            student_attendance = student_attendance[student_attendance['date'] == user_date]

            if student_attendance.empty:
                messages.error(request, 'No Records!!!')
                return render(request, 'timetable.html', content)

            student_details = pd.DataFrame(Register.objects.all().values())
            student_attendance = pd.merge(student_details, student_attendance, on='tag_id')
            group_by_student_attendance = student_attendance.groupby('id')
            content['table'] = []
            for id_, data in group_by_student_attendance:
                print('='*20)
                for row in data.sort_values(['date']).drop(['id', 'date', 'day'], axis=1).values.tolist():
                    content['table'].append(row)
            print(content['table'])
            # .to_html(classes="table table-hover", index=False))
        # ============================================================
        extra_content = {'user_date': str(user_date), 'course': course, 'day': day, 'year': year,
                         'table_head': ['Tag_ID', 'Div', 'Roll', 'Name', 'Course', 'Year', 'Area', 'Batch']}
        content.update(extra_content)
        template_path = 'timetable_pdf.html'
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{course}-{date.today()}.pdf"'
        # response['Content-Disposition'] = f'filename="{course}-{date.today()}.pdf"'
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

        content, message = None, None
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
                   'heading': ['Sr_no', 'Tag_id', 'Name', 'Course', 'Roll number', 'Division', 'In-Time', 'Out-Time'],
                   'data': content['person_list']}

        if content['teacher_list']:
            context['teacher_list'] = content['teacher_list']
            context['t_heading'] = ['Sr_no', 'Tag_id', 'Name', 'Course', 'Practical subject', 'In-Time', 'Out-Time']

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
