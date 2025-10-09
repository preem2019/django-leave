# db_manager/views.py

from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import user_passes_test

def is_superuser(user):
    return user.is_superuser

@user_passes_test(is_superuser)
def db_view(request):
    query = request.POST.get('query', 'SHOW TABLES;')
    results = []
    error = None
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
            else: # สำหรับคำสั่งที่ไม่ใช่ SELECT เช่น SHOW TABLES
                results = cursor.fetchall()

    except Exception as e:
        error = str(e)
        
    context = {
        'query': query,
        'results': results,
        'error': error,
    }
    return render(request, 'db_manager/db_view.html', context)