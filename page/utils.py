import matplotlib.pyplot as plt
from io import BytesIO
import base64
import random
import pandas as pd


def get_graph():
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    graph = base64.b64encode(image_png)
    graph = graph.decode('utf-8')
    buffer.close()
    return graph


def get_plot(x, y):
    x = list(map(lambda z: z[0], x))
    plt.switch_backend('AGG')
    plt.figure(figsize=(10, 5))
    plt.title('hello')
    plt.plot(x, y)
    plt.tight_layout()
    graph = get_graph()
    return graph


def get_x_y(record):
    x, y = [], []
    for srno, data in enumerate(record, 0):
        if srno % 2 != 0:
            y.append(data)
        else:
            x.append(data)
    return x, y


def segregate_records(dataframe, is_batch):
    courses = {}
    if not is_batch:
        for key, item in dataframe.items():
            course, year, date = key
            courses[f'{course}'] = {}
        for key, item in dataframe.items():
            course, year, date = key
            courses[f'{course}'][f'{year}'] = []
        for key, item in dataframe.items():
            course, year, date = key
            courses[f'{course}'][f'{year}'].append(date)
            courses[f'{course}'][f'{year}'].append(item)
    else:
        for key, item in dataframe.items():
            batch, date = key
            courses[batch] = {}
        for key, item in dataframe.items():
            batch, date = key
            courses[batch][batch] = []
        for key, item in dataframe.items():
            batch, date = key
            courses[batch][batch].append(date)
            courses[batch][batch].append(item)

    return courses


def combine_plot(dataframe, distinct_dates, is_bar, is_batch):

    dataframe = segregate_records(dataframe, is_batch)
    print(dataframe)
    plt.switch_backend('AGG')
    date = None

    if is_bar:
        plt.figure(figsize=(9, 5))
        count_array = []
        count_title = []
        for course, data in dataframe.items():
            for year_, item in data.items():
                date_, count_ = item
                date = date_
                count_array.append(count_)
                count_title.append(f'{course}-{year_}')

        current_course = None
        color = 'b'
        for course, count in list(zip(count_title, count_array)):
            course_now = course.split('-')[0]

            if current_course != course_now:
                color = [random.uniform(0.1, 1) for _ in range(3)]
                current_course = course_now
            plt.bar(course, count, color=color)

        plt.xlabel('courses\n')
        plt.ylabel('Count of attendance')
        plt.title(f'Bar plot for {date}')
        plt.xticks(count_title, rotation=90)
        plt.tight_layout()
        plt.grid()

        graph = get_graph()
    else:
        plt.figure(figsize=(9, 5))
        plt.title('Combine plot')

        for srno, (course, data) in enumerate(dataframe.items(), start=1):
            ls = ['-', '--', '-.', ':']
            for year, record in data.items():
                x, y = get_x_y(record)
                if is_batch:
                    plt.plot(x, y, label=f'{year}', linestyle=ls[srno % 4], linewidth=random.uniform(2, 10))
                else:
                    plt.plot(x, y, label=f'{course}-{year}', linestyle=ls[srno % 4], linewidth=random.uniform(2, 10))

        plt.xlabel('Dates')
        plt.ylabel('Count of attendance')
        plt.xticks(distinct_dates, rotation=90)
        plt.legend(loc='best')
        plt.tight_layout()
        plt.grid()
        graph = get_graph()
    return graph


def segregate_records_comparision(dataframe):
    courses = {}
    for key, item in dataframe.items():
        year, date = key
        courses[f'{year}'] = []
    for key, item in dataframe.items():
        year, date = key
        courses[f'{year}'].append(date)
        courses[f'{year}'].append(item)
    return courses


def comparision_plot(dataframe, distinct_dates, course, is_bar):
    dataframe = segregate_records_comparision(dataframe)
    plt.switch_backend('AGG')

    if is_bar:
        year = None
        plt.figure(figsize=(7, 4))
        count_array = []
        count_title = []
        for year_, data in dataframe.items():
            year = year_
            count_array.append(data[1])
            count_title.append(f'{year_}')

        plt.bar(count_title, count_array)

        plt.xlabel('courses\n')
        plt.ylabel('Count of attendance')
        if year:
            plt.title(f'Comparision plot for {course}-{year}')
        else:
            plt.title(f'Comparision plot for {course}')
        plt.tight_layout()
        plt.grid()
        graph = get_graph()
    else:
        plt.figure(figsize=(7, 4))
        plt.title(f'Comparision plot for {course}')
        for srno, (year, data) in enumerate(dataframe.items(), start=1):
            ls = ['-', '--', '-.', ':']
            x, y = get_x_y(data)
            plt.plot(x, y, label=f'{year}', linestyle=ls[srno % 4], linewidth=random.uniform(2, 10))

        plt.xlabel('Dates')
        plt.ylabel('Count of attendance')
        plt.xticks(distinct_dates, rotation=90)
        plt.legend(loc='best')
        plt.tight_layout()
        plt.grid()
        graph = get_graph()
    return graph
