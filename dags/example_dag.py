"""
Example Airflow DAG for testing AKS deployment
This DAG demonstrates basic functionality and can be used to verify your deployment
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def print_hello():
    """Simple Python function"""
    print("Hello from Airflow in AKS!")
    return "Success"

def print_date():
    """Print current date"""
    print(f"Current date and time: {datetime.now()}")
    return datetime.now()

with DAG(
    dag_id='example_aks_dag',
    default_args=default_args,
    description='Example DAG for AKS deployment testing',
    schedule_interval=timedelta(days=1),
    catchup=False,
    tags=['example', 'aks'],
) as dag:
    
    # Task 1: Bash operator
    start_task = BashOperator(
        task_id='start',
        bash_command='echo "Starting DAG execution in AKS"',
    )
    
    # Task 2: Python operator
    hello_task = PythonOperator(
        task_id='print_hello',
        python_callable=print_hello,
    )
    
    # Task 3: Python operator
    date_task = PythonOperator(
        task_id='print_date',
        python_callable=print_date,
    )
    
    # Task 4: Bash operator
    end_task = BashOperator(
        task_id='end',
        bash_command='echo "DAG execution completed successfully"',
    )
    
    # Define task dependencies
    start_task >> hello_task >> date_task >> end_task

