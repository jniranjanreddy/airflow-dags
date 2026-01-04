"""
Example DAG for Testing Airflow 3.x
This DAG demonstrates basic Airflow concepts
"""
from datetime import datetime, timedelta
from airflow import DAG
# Airflow 3.x uses providers.standard instead of operators
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator

# Default arguments for all tasks
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
with DAG(
    dag_id='example_test_dag',
    default_args=default_args,
    description='A simple example DAG for testing',
    schedule='@daily',  # Run once a day
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['example', 'test'],
) as dag:

    # Task 1: Start (Empty operator - does nothing, just marks start)
    start = EmptyOperator(
        task_id='start',
    )

    # Task 2: Print hello using Python
    def print_hello():
        print("Hello from Airflow!")
        return "Hello task completed"

    hello_task = PythonOperator(
        task_id='hello_python',
        python_callable=print_hello,
    )

    # Task 3: Run a bash command
    bash_task = BashOperator(
        task_id='bash_echo',
        bash_command='echo "Current date: $(date)" && echo "Airflow is working!"',
    )

    # Task 4: Another Python task that processes data
    def process_data(**context):
        """Simulate data processing"""
        # Airflow 3.x uses logical_date instead of execution_date
        logical_date = context['logical_date']
        print(f"Processing data for: {logical_date}")
        
        # Simulate some work
        data = {'records_processed': 100, 'status': 'success'}
        print(f"Result: {data}")
        return data

    process_task = PythonOperator(
        task_id='process_data',
        python_callable=process_data,
    )

    # Task 5: End
    end = EmptyOperator(
        task_id='end',
    )

    # Define task dependencies (execution order)
    # start -> [hello_task, bash_task] -> process_task -> end
    start >> [hello_task, bash_task] >> process_task >> end

