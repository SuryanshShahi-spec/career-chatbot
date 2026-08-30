import psycopg2

try:
    print("Forcing connection with user 'postgres' on port 5432...")
    
    connection = psycopg2.connect(
        host="localhost",
        database="postgres",   
        user="postgres",       
        password="YOUR_ACTUAL_PASSWORD_HERE",  
        port="5432"
    )
    
    print("🎉 SUCCESS! The connection is fixed!")
    connection.close()

except Exception as error:
    print(f"\n❌ Connection failed: {error}")
