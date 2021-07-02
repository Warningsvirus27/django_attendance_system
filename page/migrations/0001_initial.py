# Generated by Django 3.2.4 on 2021-06-09 21:18

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='LocationTrack',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('area', models.CharField(max_length=40)),
                ('tag_id_id', models.IntegerField()),
                ('date', models.DateField(auto_now_add=True)),
                ('time', models.TimeField(auto_now_add=True)),
                ('status', models.CharField(max_length=3)),
            ],
        ),
        migrations.CreateModel(
            name='Register',
            fields=[
                ('tag_id', models.IntegerField(primary_key=True, serialize=False, unique=True)),
                ('div', models.CharField(max_length=3)),
                ('roll', models.IntegerField()),
                ('name', models.CharField(max_length=80)),
                ('course', models.CharField(max_length=30)),
                ('year', models.CharField(max_length=3)),
            ],
        ),
        migrations.CreateModel(
            name='TeacherRegister',
            fields=[
                ('t_name', models.CharField(max_length=80)),
                ('tag_id', models.IntegerField(primary_key=True, serialize=False)),
                ('course', models.CharField(choices=[('BSc.Computer Science', 'BSc.Computer Science'), ('BSc.Computer Application', 'BSc.Computer Application'), ('BSc.IT Cyber Crime', 'BSc.IT Cyber Crime'), ('BCom', 'BCom'), ('BBA', 'BBA'), ('MBA', 'MBA'), ('MSc.Computer Science', 'MSc.Computer Science'), ('MSc.Computer Application', 'MSc.Computer Application')], max_length=30)),
                ('practical_subject', models.CharField(max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name='Timetable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course', models.CharField(choices=[('BSc.Computer Science', 'BSc.Computer Science'), ('BSc.Computer Application', 'BSc.Computer Application'), ('BSc.IT Cyber Crime', 'BSc.IT Cyber Crime'), ('BCom', 'BCom'), ('BBA', 'BBA'), ('MBA', 'MBA'), ('MSc.Computer Science', 'MSc.Computer Science'), ('MSc.Computer Application', 'MSc.Computer Application')], max_length=30)),
                ('year', models.CharField(choices=[('FY', 'FY'), ('SY', 'SY'), ('TY', 'TY')], max_length=12)),
                ('area', models.CharField(max_length=40)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('Monday', models.CharField(max_length=30)),
                ('Tuesday', models.CharField(max_length=30)),
                ('Wednesday', models.CharField(max_length=30)),
                ('Thursday', models.CharField(max_length=30)),
                ('Friday', models.CharField(max_length=30)),
                ('Saturday', models.CharField(max_length=30)),
                ('Sunday', models.CharField(max_length=30)),
            ],
        ),
    ]