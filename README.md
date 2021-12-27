# django_attendance_system

The website is meant to store attendances of students based on their taps (rfid-tag taps).
The raspberry pi along with rfid module(rc522) will capture the timestamp and location of tap(particular lab or room) of students who have tapped on rc522, and send a https request to website rest api, the api would verify the tags and store the details. Teachers can save attendances based on these timestamp. 

The website can download Pdfs, Excels for all webpages, <br>
it can trace any student/teacher based on their taps,<br>
can view timetable wise list of students, <br>
can view the timewise list of students for any particular room/lab,<br> 
has rest api framework, <br>
has default django admin panel, <br>
can analyse attendances with graphs<br>
-> distinct courses, distinct year, distinct date vs total count of attendance; <br>
-> particular courses, distinct batches, distinct date vs total count of attendance; <br>
likewise.<br>
