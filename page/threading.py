from django.db import connection
from datetime import date, datetime
import threading
from .models import AttendanceRecord


class SaveAttendanceThread(threading.Thread):

    def __init__(self, user_date=None):
        threading.Thread.__init__(self)
        self.user_date = user_date

    def run(self):
        cursor = connection.cursor()
        cursor.execute(f"select distinct(page_timetable.course) from page_timetable;")
        courses = cursor.fetchall()
        if self.user_date:
            user_date = self.user_date
            split_list_of_date = user_date.split('-')
            day = date(int(split_list_of_date[0]), int(split_list_of_date[1]), int(split_list_of_date[2]))
            day = day.strftime('%A')
        else:
            day = datetime.today().strftime("%A")
            user_date = date.today()
        # extracting data from excel file regarding the given course
        if courses:
            for course in courses:
                cursor = connection.cursor()
                cursor.execute(f'''select distinct(page_timetable.year) from page_timetable where course='{course[0]}';''')
                years = cursor.fetchall()
                for year in years:

                    cursor.execute(f'''select page_timetable.start_time,page_timetable.end_time,page_timetable.area,
                        page_timetable."{day}" from page_timetable where course='{course[0]}' and 
                        year='{year[0]}';''')
                    year_data = cursor.fetchall()

                    count, students, batches, batch_time, location = return_std_details(year_data, user_date)

                    if any(students):
                        iterator = 0

                        for student in students:
                            for individual in student:
                                status = self.check_existence(course[0], year[0], individual, batches[iterator],
                                                              location[iterator], user_date, day)

                                if status:
                                    self.add_to_records(course[0], year[0], batch_time[iterator], count[iterator][0],
                                                        individual, batches[iterator], location[iterator], user_date,
                                                        day)
                            iterator += 1

    def check_existence(self, course, year, individual, batch, location, user_date, day):
        cursor = connection.cursor()
        cursor.execute(f"""select page_attendancerecord.std_name from page_attendancerecord where
                            page_attendancerecord.course = '{course}' and 
                            page_attendancerecord.academic_year = '{year}' and 
                            page_attendancerecord.attendance_date = '{user_date}' and 
                            page_attendancerecord.attendance_day = '{day}' and 
                            page_attendancerecord.attendance_location = '{location}' and 
                            page_attendancerecord.attendance_batch = '{batch}' and 
                            page_attendancerecord.std_roll = '{individual[2]}' ;""")
        data = cursor.fetchone()
        if not data:
            return True
        else:
            return False

    def add_to_records(self, course, year, batch_time, count, individual, batch, location, user_date, day):
        start_time = batch_time[:8]
        end_time = batch_time[9:]
        name, div, roll, tag_id = individual

        std = AttendanceRecord()
        std.course = course
        std.academic_year = year
        std.start_time = start_time
        std.end_time = end_time
        std.attendance_date = user_date
        std.attendance_count = count
        std.std_name = name
        std.std_roll = roll
        std.std_div = div
        std.attendance_batch = batch
        std.attendance_location = location
        std.attendance_day = day
        std.tag_id = tag_id
        std.save()


def return_std_details(timetable, user_date):
    # declaring dist_count and person_list_per_lect list so that the return statement runs well

    batch_count = []
    table = []
    batch_time = []
    batch_location = []
    iterator = 0
    person_list_per_lect = []
    for lecture in timetable:

        dist_count = []

        table.append(lecture[3])
        start_time, end_time, area = str(lecture[0]), str(lecture[1]), lecture[2]
        batch_location.append(area)

        batch_time.append(str(start_time) + '-' + str(end_time))

        start_hour, start_minute = start_time[:2], start_time[3:5]
        end_hour, end_minute = end_time[:2], end_time[3:5]

        if int(start_minute) < 10:
            start_minute = 50 + int(start_minute)
            start_hour = int(start_hour) - 1
        else:
            start_minute = int(start_minute) - 10

        if int(end_minute) > 50:
            end_minute = int(end_minute) - 50
            end_hour = int(end_hour) + 1
        else:
            end_minute = int(end_minute) + 10

        cursor = connection.cursor()
        cursor.execute(f"""select page_locationtrack.tag_id_id from page_locationtrack, page_teacherregister where 
                                page_locationtrack.area='{area}' and 
                                page_locationtrack.time >= '{start_hour}:{start_minute}:00' and 
                                page_locationtrack.time <= '{end_hour}:{end_minute}:00' 
                                and page_locationtrack.date = '{user_date}' and page_locationtrack.status = 'IN'
                                and page_locationtrack.tag_id_id = page_teacherregister.tag_id
                                order by page_locationtrack.time;""")
        teacher_tag_id = cursor.fetchone()

        if teacher_tag_id:
            cursor.execute(f"""select time from page_locationtrack where tag_id_id = '{teacher_tag_id[0]}'
                                and area = '{area}' and time >= '{start_hour}:{start_minute}:00' and 
                                    time <= '{end_hour}:{end_minute}:00' 
                                    and date = '{user_date}' and status = 'OUT';""")
            pract_end_time = cursor.fetchone()
        else:
            pract_end_time = None

        if pract_end_time:
            pract_end_time = str(pract_end_time[0])
            pract_end_hour = int(str(pract_end_time[:2]))
            pract_end_minute = int(str(pract_end_time[3:5]))

            if pract_end_minute < 10:
                start_minute = 50 + pract_end_minute
                start_hour = pract_end_hour - 1
            else:
                start_hour = pract_end_hour
                start_minute = pract_end_minute - 10

            if pract_end_minute > 50:
                end_minute = pract_end_minute - 50
                end_hour = pract_end_hour + 1
            else:
                end_hour = pract_end_hour
                end_minute = pract_end_minute + 10

            cursor = connection.cursor()
            cursor.execute(f"""select distinct(tag_id_id) from page_locationtrack
                                where time >= '{start_hour}:{start_minute}:00'
                                and time <= '{end_hour}:{end_minute}:00' and status = 'OUT' and area = '{area}' and 
                                date = '{user_date}' and tag_id_id not in (select tag_id from page_teacherregister);""")
            total_students = cursor.fetchall()

            student_detail_list = []
            temp = 0
            for person in total_students:
                if person:
                    cursor = connection.cursor()
                    cursor.execute(f"""select name, div, roll from page_register, page_locationtrack where 
                                                                page_register.tag_id = '{person[0]}';""")
                    stud_det = cursor.fetchone()
                    student_detail_list.append([stud_det[0], stud_det[1], stud_det[2], person[0]])
                    temp += 1

            person_list_per_lect.append(student_detail_list)
            dist_count.append(temp)

        if not pract_end_time:
            dist_count.append('No Teacher')
            iterator += 1
        batch_count.append(dist_count)
    return batch_count, person_list_per_lect, table, batch_time, batch_location
