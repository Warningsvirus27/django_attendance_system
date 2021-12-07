from django.db import models
from django.utils import timezone

course_choices = [
    ("BSc.Computer Science", "BSc.Computer Science"),
    ("BSc.Computer Application", "BSc.Computer Application"),
    ("BSc.IT Cyber Crime", "BSc.IT Cyber Crime"),
    ("BCom", "BCom"),
    ("BBA", "BBA"),
    ("MBA", "MBA"),
    ("MSc.Computer Science", "MSc.Computer Science"),
    ("MSc.Computer Application", "MSc.Computer Application")
]
location_choices = [
    ('Computer Lab 1-a', 'Computer Lab 1-a'),
    ('Computer Lab 1-b', 'Computer Lab 1-b'),
    ('Computer Lab 2-a', 'Computer Lab 2-a'),
    ('Computer Lab 2-b', 'Computer Lab 2-b'),
    ('Computer Lab 3-a', 'Computer Lab 3-a'),
    ('Computer Lab 3-b', 'Computer Lab 3-b'),
    ('Computer Lab 4-a', 'Computer Lab 4-a'),
    ('Computer Lab 4-b', 'Computer Lab 4-b'),
    ('Electronics lab', 'Electronics lab'),
    ('Sports Room', 'Sports Room'),
    ('Library', 'Library')
]


class Register(models.Model):
    tag_id = models.CharField(primary_key=True, unique=True, max_length=15)
    div = models.CharField(max_length=3)
    roll = models.IntegerField()
    name = models.CharField(max_length=80)
    course = models.CharField(max_length=30, choices=course_choices)
    year = models.CharField(max_length=3)

    def __str__(self):
        return self.name


class TeacherRegister(models.Model):
    t_name = models.CharField(max_length=80)
    tag_id = models.CharField(primary_key=True, unique=(not Register.tag_id), max_length=15)
    course = models.CharField(choices=course_choices, max_length=30)
    practical_subject = models.CharField(max_length=80)

    def __str__(self):
        return self.t_name


class LocationTrack(models.Model):
    status = [
        ('IN', 'IN'),
        ('OUT', 'OUT')
    ]
    area = models.CharField(max_length=40, choices=location_choices)
    tag_id_id = models.CharField(max_length=15)
    date = models.DateField(default=timezone.now, editable=True)
    time = models.TimeField(default=timezone.now, editable=True)
    status = models.CharField(max_length=3, choices=status)

    def __str__(self):
        return f'{self.area} {self.tag_id_id} {self.status}'


class Timetable(models.Model):
    year_list = [
        ('FY', 'FY'),
        ('SY', 'SY'),
        ('TY', 'TY')
    ]
    student = models.ManyToManyField(Register, through='AttendanceRecord', editable=False)
    course = models.CharField(choices=course_choices, max_length=30)
    year = models.CharField(choices=year_list, max_length=12)
    area = models.CharField(max_length=40, choices=location_choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    Monday = models.CharField(max_length=30)
    Tuesday = models.CharField(max_length=30)
    Wednesday = models.CharField(max_length=30)
    Thursday = models.CharField(max_length=30)
    Friday = models.CharField(max_length=30)
    Saturday = models.CharField(max_length=30)
    Sunday = models.CharField(max_length=30)

    def __str__(self):
        return f'{self.course}  {self.year} {str(self.start_time)} {str(self.end_time)}'


class AttendanceRecord(models.Model):
    student = models.ForeignKey(Register, on_delete=models.CASCADE)
    attendance = models.ForeignKey(Timetable, on_delete=models.CASCADE)
    area = models.CharField(max_length=40)
    date = models.DateField()
    day = models.CharField(max_length=20)
    batch = models.CharField(max_length=25)

    def __str__(self):
        return str(self.date)



