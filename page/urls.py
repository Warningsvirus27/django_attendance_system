from django.urls import path
from . import views

app_name = 'page'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('logout/', views.logout, name='l_out'),
    path('register/', views.register_data, name='register'),
    path('trace/<str:method>/', views.trace_card, name='trace'),
    path('trace/', views.trace_card, name='trace'),
    path('count/', views.count_person, name='count'),
    path('entry/', views.entry_data, name='entry'),
    path('timetable_wise-count/', views.timetable_wise_count, name='timetable_wise_count'),
    path('time_wise-count/', views.time_wise_count, name='time_wise_count'),
    path('weekly_data/', views.weekly_data, name='weekly_data'),
    path('monthly_data/', views.monthly_data, name='monthly_data'),
    path('view_timetable/', views.view_timetable, name='view_timetable'),
    path('analyse_attendance/', views.analyse_attendance, name='analyse_attendance'),

    path('excel-trace/', views.trace_excel, name='trace_excel'),
    path('excel-time_wise_count/', views.time_wise_excel, name='excel-time_wise_excel'),
    path('excel-timetable_count/', views.timetable_wise_excel, name='timetable_excel'),
    path('time_wise_pdf/', views.time_wise_pdf, name='time_wise_pdf'),
    path('timetable_pdf/', views.timetable_pdf, name='timetable_pdf'),
    path('trace_pdf/', views.trace_pdf, name='trace_pdf'),
    path('what_is_rfid/', views.what_is_rfid, name='what_is_rfid'),
    path('why_rfid/', views.why_rfid, name='why_rfid'),
    path('how_it_works/', views.how_it_works, name='how_it_works'),
    path('weekly-monthly_excel_pdf/<str:method>/', views.weekly_monthly_excel_pdf, name='weekly-monthly_excel_pdf'),
    path('weekly-monthly_excel_pdf/', views.weekly_monthly_excel_pdf, name='weekly-monthly_excel_pdf'),

    path('entry_/', views.TagApiView.as_view(), name='entry_'),
    path('entry_/<str:tag_>/<str:area_>/', views.TagApiView.as_view(), name='entry_')

]
