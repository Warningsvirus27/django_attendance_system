from .models import TeacherRegister


def return_count_value(timetable, date):
    from django.db import connection
    # declaring dist_count and person_list_per_lect list so that the return statement runs well
    batch_list = []
    batch_count = []
    table = []
    batch_time = []
    batch_location = []
    batch_wise_person_dict = {}
    iterator = 0

    for lecture in timetable:

        dist_count = []
        person_list_per_lect = []
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
                                and page_locationtrack.date = '{date}' and page_locationtrack.status = 'IN'
                                and page_locationtrack.tag_id_id = page_teacherregister.tag_id
                                order by page_locationtrack.time;""")
        teacher_tag_id = cursor.fetchone()

        if teacher_tag_id:
            cursor.execute(f"""select time from page_locationtrack where tag_id_id = '{teacher_tag_id[0]}'
                                and area = '{area}' and time >= '{start_hour}:{start_minute}:00' and 
                                    time <= '{end_hour}:{end_minute}:00' 
                                    and date = '{date}' and status = 'OUT';""")
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
                                date = '{date}' and tag_id_id not in (select tag_id from page_teacherregister);""")
            total_students = cursor.fetchall()

            student_detail_list = []
            temp = 0
            for person in total_students:
                if person:
                    cursor = connection.cursor()
                    cursor.execute(f"""select name, div, roll from page_register, page_locationtrack where 
                                                                page_register.tag_id = '{person[0]}';""")
                    stud_det = cursor.fetchone()
                    student_detail_list.append([stud_det[0], stud_det[1], stud_det[2]])
                    temp += 1

            person_list_per_lect.append(student_detail_list)
            dist_count.append(temp)
            # person_list_per_lect = transpose(person_list_per_lect)
            if not any(total_students):
                batch_wise_person_dict[f'{iterator}'] = []
            else:
                batch_wise_person_dict[f'{iterator}'] = transpose(person_list_per_lect)
            iterator += 1

        if not pract_end_time:
            batch_wise_person_dict[f'{iterator}'] = []
            dist_count.append('No Teacher')
            iterator += 1
        # batch_list.append(person_list_per_lect)
        batch_count.append(dist_count)
    batch_list = batch_wise_maker(batch_wise_person_dict)

    return batch_count, batch_list, table, batch_time, batch_location


def batch_wise_maker(person_dict):
    temp_list = []
    max_len = 0
    for key in person_dict:
        if len(person_dict[key]) > max_len:
            max_len = len(person_dict[key])

    for x in range(max_len):
        temp = []
        for key in person_dict:
            try:
                if person_dict[key][x]:
                    temp.append(person_dict[key][x])
            except:
                temp.append([])
        temp_list.append(temp)
    return temp_list


def convert_date(user_date):
    user_date = [x.replace('(', '') for x in user_date]
    user_date = [x.replace(')', '') for x in user_date]
    user_date = [x.replace(',', '-') for x in user_date]
    user_date = [x.replace(' ', '') for x in user_date]
    user_date = ''.join(user_date)
    return user_date


def transpose(matrix):
    if not matrix:
        return []

    cols = 0
    for x in matrix:
        if cols < len(x):
            cols = len(x)
    i = 0
    for x in matrix:
        if len(x) == cols:
            i += 1
            continue
        diff = abs(cols - len(x))
        if x == [['break']]:
            for y in range(diff):
                x.append(['break'])
                continue
        for y in range(diff):
            matrix[i].append([])
        i += 1
    rows = len(matrix)
    cols = len(matrix[0])

    transposed = []
    while len(transposed) < cols:
        transposed.append([])
        while len(transposed[-1]) < rows:
            transposed[-1].append(0)

    for i in range(rows):
        for j in range(cols):
            transposed[j][i] = matrix[i][j]

    return transposed


def get_date():
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute(f"select distinct(date) from page_locationtrack order by date desc;")
    dates_from_table = cursor.fetchall()
    date_list = []
    for x in dates_from_table:
        x = x[0]
        x = str(x)
        # date_list.append(x[14:27])
        date_list.append(x)
    return date_list


def teacher_list():
    teachers = TeacherRegister.objects.all()
    return teachers


def count_for_entire_day(place_to_find_count, user_date, start_minute, end_minute):
    from django.db import connection
    data_list = []
    teacher_data_list = []
    cursor = connection.cursor()
    cursor.execute(f"""select page_register.tag_id,page_register.name,page_register.course,page_register.roll,page_register.div,
    page_locationtrack.time,page_locationtrack.status from page_register, page_locationtrack where
                        page_register.tag_id = page_locationtrack.tag_id_id and area='{place_to_find_count}'
                        and page_locationtrack.date = '{user_date}' order by page_locationtrack.time;""")
    stud_data = cursor.fetchall()
    cursor.execute(f"""select page_teacherregister.tag_id,page_teacherregister.t_name,page_teacherregister.course,
    page_teacherregister.practical_subject,page_locationtrack.time,page_locationtrack.status from
                    page_teacherregister, page_locationtrack where
                                    page_teacherregister.tag_id = page_locationtrack.tag_id_id and
                                    area='{place_to_find_count}'
                                    and page_locationtrack.date = '{user_date}' order by page_locationtrack.time;""")
    teacher_data = cursor.fetchall()
    cursor = connection.cursor()
    cursor.execute(f"""select count(distinct(tag_id_id)) from page_locationtrack where
                               area='{place_to_find_count}' and date='{user_date}';""")
    distinct_count = cursor.fetchall()
    cursor = connection.cursor()
    cursor.execute(f"""select count(tag_id_id) from page_locationtrack where
                                           area='{place_to_find_count}' and date='{user_date}';""")
    total_count = cursor.fetchall()

    for srno, (tag, name, course, roll, div, time, status) in enumerate(stud_data, 1):
        data_list.append([srno, tag, name, course, roll, div, time, status])
    for srno, (tag, name, course, practical_subject, time, status) in enumerate(teacher_data, 1):
        teacher_data_list.append([srno, tag, name, course, practical_subject, time, status])

    if start_minute and not end_minute:
        messages = '''Start Minute will not count! Showing count for entire day'''
        content = {"person_list": data_list,
                   "teacher_list": teacher_data_list,
                   "distinct_count": distinct_count[0][0],
                   'total_count': total_count[0][0]}
    elif end_minute and not start_minute:
        messages = '''End Minute will not count! Showing count for entire day'''
        content = {"person_list": data_list,
                   "teacher_list": teacher_data_list,
                   "distinct_count": distinct_count[0][0],
                   'total_count': total_count[0][0]}
    elif start_minute and end_minute:
        messages = '''Start Minute and End Minute will not count! Showing count for entire day'''
        content = {"person_list": data_list,
                   "teacher_list": teacher_data_list,
                   "distinct_count": distinct_count[0][0],
                   'total_count': total_count[0][0]}

    else:
        messages = "Showing count for entire day!"
        content = {"person_list": data_list,
                   "teacher_list": teacher_data_list,
                   "distinct_count": distinct_count[0][0],
                   'total_count': total_count[0][0]}

    return messages, content


def count_with_starting_time(start_minute, start_time, place_to_find_count, user_date):
    from django.db import connection
    data_list = []
    teacher_data_list = []
    if not start_minute:
        start_minute = '00'
    cursor = connection.cursor()
    cursor.execute(f"""select page_register.tag_id,page_register.name,page_register.course,page_register.roll,page_register.div,
    page_locationtrack.time,page_locationtrack.status from page_register, page_locationtrack where
                        page_register.tag_id = page_locationtrack.tag_id_id and area='{place_to_find_count}'
                    and page_locationtrack.time>='{start_time}:{start_minute}:00'
                    and page_locationtrack.date = '{user_date}' order by page_locationtrack.time;""")
    data = cursor.fetchall()
    cursor.execute(f"""select page_teacherregister.tag_id,page_teacherregister.t_name,page_teacherregister.course,page_teacherregister.practical_subject,
    page_locationtrack.time,page_locationtrack.status from
                        page_teacherregister, page_locationtrack where
                                    page_teacherregister.tag_id = page_locationtrack.tag_id_id and
                                    area='{place_to_find_count}'
                                    and page_locationtrack.date = '{user_date}' order by page_locationtrack.time;""")
    teacher_data = cursor.fetchall()
    for srno, (tag, name, course, practical_subject, time, status) in enumerate(teacher_data, 1):
        teacher_data_list.append([srno, tag, name, course, practical_subject, time, status])
    for srno, (tag, name, course, roll, div, time, status) in enumerate(data, 1):
        data_list.append([srno, tag, name, course, roll, div, time, status])

    cursor = connection.cursor()
    cursor.execute(f"""select count(distinct(tag_id_id)) from page_locationtrack where
                               area='{place_to_find_count}' and date='{user_date}'
                            and time>='{start_time}:{start_minute}:00';""")
    distinct_count = cursor.fetchall()
    cursor = connection.cursor()
    cursor.execute(f"""select count(tag_id_id) from page_locationtrack where
                                           area='{place_to_find_count}' and date='{user_date}'
                                        and time>='{start_time}:{start_minute}:00';""")
    total_count = cursor.fetchall()
    message = f"Showing student count from time {start_time}:{start_minute}:00 onwards"
    content = {"person_list": data_list,
               "teacher_list": teacher_data_list,
               "distinct_count": distinct_count[0][0],
               'total_count': total_count[0][0]}
    return message, content


def count_with_ending_time(end_minute, end_time, place_to_find_count, user_date):
    from django.db import connection
    data_list = []
    teacher_data_list = []
    if not end_minute:
        end_minute = '00'
    cursor = connection.cursor()
    cursor.execute(f"""select page_register.tag_id, page_register.name, page_register.course, page_register.roll, page_register.div,
    page_locationtrack.time, page_locationtrack.status from page_register, page_locationtrack where
                        page_register.tag_id = page_locationtrack.tag_id_id and area='{place_to_find_count}'
                    and page_locationtrack.time<='{end_time}:{end_minute}:00'
                    and page_locationtrack.date = '{user_date}' order by page_locationtrack.time;""")
    data = cursor.fetchall()
    cursor.execute(f"""select page_teacherregister.tag_id,page_teacherregister.t_name,page_teacherregister.course,page_teacherregister.practical_subject,
    page_locationtrack.time,page_locationtrack.status from
                            page_teacherregister, page_locationtrack where
                                        page_teacherregister.tag_id = page_locationtrack.tag_id_id and
                                        area='{place_to_find_count}'
                                        and page_locationtrack.date = '{user_date}'
                                        order by page_locationtrack.time;""")
    teacher_data = cursor.fetchall()
    for srno, (tag, name, course, practical_subject, time, status) in enumerate(teacher_data, 1):
        teacher_data_list.append([srno, tag, name, course, practical_subject, time, status])
    for srno, (tag, name, course, roll, div, time, status) in enumerate(data, 1):
        data_list.append([srno, tag, name, course, roll, div, time, status])

    cursor.execute(f"""select count(distinct(tag_id_id)) from page_locationtrack where
                                           area='{place_to_find_count}' and date='{user_date}'
                                        and time<='{end_time}:{end_minute}:00';""")
    distinct_count = cursor.fetchall()
    cursor.execute(f"""select count(tag_id_id) from page_locationtrack where
                                                       area='{place_to_find_count}' and date='{user_date}'
                                                    and time<='{end_time}:{end_minute}:00';""")
    total_count = cursor.fetchall()
    message = f"Showing student count before time {end_time}:{end_minute}:00"
    content = {"person_list": data_list,
               "teacher_list": teacher_data_list,
               "distinct_count": distinct_count[0][0],
               'total_count': total_count[0][0]}
    return message, content


def count_with_start_end_time(start_minute, end_minute, start_time, end_time, place_to_find_count, user_date):
    from django.db import connection
    data_list = []
    teacher_data_list = []
    if not start_minute and not end_minute:
        start_minute = '00'
        end_minute = '00'
    if not start_minute and end_minute:
        start_minute = '00'
    if start_minute and not end_minute:
        end_minute = '00'
    cursor = connection.cursor()
    cursor.execute(f"""select page_register.tag_id, page_register.name, page_register.course,page_register.roll, page_register.div,
    page_locationtrack.time, page_locationtrack.status from page_register, page_locationtrack where
                page_register.tag_id = page_locationtrack.tag_id_id and area='{place_to_find_count}'
                and page_locationtrack.time>='{start_time}:{start_minute}:00'
                and page_locationtrack.time<='{end_time}:{end_minute}:00'
                and page_locationtrack.date = '{user_date}' order by page_locationtrack.time;""")
    data = cursor.fetchall()
    cursor.execute(f"""select page_teacherregister.tag_id,page_teacherregister.t_name,page_teacherregister.course,page_teacherregister.practical_subject,
    page_locationtrack.time,page_locationtrack.status from
                            page_teacherregister, page_locationtrack where
                                        page_teacherregister.tag_id = page_locationtrack.tag_id_id and
                                        area='{place_to_find_count}'
                                        and page_locationtrack.date = '{user_date}'
                                        order by page_locationtrack.time;""")
    teacher_data = cursor.fetchall()
    for srno, (tag, name, course, practical_subject, time, status) in enumerate(teacher_data, 1):
        teacher_data_list.append([srno, tag, name, course, practical_subject, time, status])

    for srno, (tag, name, course, roll, div, time, status) in enumerate(data, 1):
        data_list.append([srno, tag, name, course, roll, div, time, status])

    cursor.execute(f"""select count(distinct(tag_id_id)) from page_locationtrack where
                    area='{place_to_find_count}' and date='{user_date}'
                    and time>='{start_time}:{start_minute}:00'
                    and time<='{end_time}:{end_minute}:00';""")
    distinct_count = cursor.fetchall()
    cursor.execute(f"""select count(tag_id_id) from page_locationtrack where
                                area='{place_to_find_count}' and date='{user_date}'
                                and time>='{start_time}:{start_minute}:00'
                                and time<='{end_time}:{end_minute}:00';""")
    total_count = cursor.fetchall()
    content = {"person_list": data_list,
               "teacher_list": teacher_data_list,
               "distinct_count": distinct_count[0][0],
               'total_count': total_count[0][0],
               'time': f"The feed is from {start_time}:{start_minute}:00 to {end_time}:{end_minute}:00"}
    return content


def input_excel_data(row_num, font_style, ws, content, iterator):
    row_num += 3
    font_style.font.bold = True

    for x in range(1, iterator):
        ws.write(row_num, 0, content[f'head{x}'], font_style)
        font_style.font.bold = False
        row_num += 1
        ws.write(row_num, 0, 'Batches', font_style)
        for col, info in enumerate(content[f'table{x}'], 2):
            ws.write(row_num, col, info, font_style)
        row_num += 1

        ws.write(row_num, 0, 'Location', font_style)
        for col, info in enumerate(content[f'area{x}'], 2):
            ws.write(row_num, col, info, font_style)
        row_num += 1
        ws.write(row_num, 0, 'Batches Time', font_style)
        for col, info in enumerate(content[f'batch_time{x}'], 2):
            ws.write(row_num, col, info, font_style)
        row_num += 1

        ws.write(row_num, 0, 'Distinct Count', font_style)
        for col, info in enumerate(content[f'dist_count{x}'], 2):
            ws.write(row_num, col, str(info[0]), font_style)

        row_num += 1
        ws.write(row_num, 0, 'Attendence List', font_style)
        for single_line in content[f'person_list{x}']:
            for sr_no, info in enumerate(single_line, 2):
                if not any(info):
                    ws.write(row_num, sr_no, '-', font_style)
                else:
                    ws.write(row_num, sr_no, f'{info[0][0]} {info[0][1]}-{info[0][2]}', font_style)
            row_num += 1
        row_num += 3
    return ws


def excel_maker_data_entry(row_num, font_style, ws, area, table):
    row_num += 3
    font_style.font.bold = True
    ws.write(row_num, 0, 'Weekly entries in', font_style)
    ws.write(row_num, 1, str(area[0][0]), font_style)
    font_style.font.bold = False
    row_num += 3

    if table == 'student':
        heading = ['Area', 'Date', 'Time', 'Tag_id', 'Name', 'Course', 'Div', 'Roll']
    else:
        heading = ['Area', 'Date', 'Time', 'Tag_id', 'Name', 'Course', 'Practical Subject']

    for col, head in enumerate(heading, 0):
        ws.write(row_num, col, head, font_style)

    row_num += 1
    for single_line in area:
        for col, data in enumerate(single_line, 0):
            ws.write(row_num, col, str(data), font_style)
        row_num += 1
    return ws, row_num + 3
