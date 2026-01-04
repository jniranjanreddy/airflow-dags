"""
Git Sync Test DAG
This DAG confirms that Git Sync is working correctly!
"""
from datetime import datetime
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.bash import BashOperator

def print_gitsync_message():
    """Print a message confirming Git Sync is working"""
    print("=" * 60)
    print("🎉 SUCCESS! This DAG was deployed via Git Sync!")
    print("=" * 60)
    print(f"Execution Time: {datetime.now()}")
    print("Repository: https://github.com/jniranjanreddy/airflow-dags")
    print("Branch: main")
    print("=" * 60)
    return "Git Sync is working!"

with DAG(
    dag_id='gitsync_test',
    description='Test DAG to confirm Git Sync is working',
    schedule=None,  # Manual trigger only
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['test', 'gitsync'],
) as dag:

    print_message = PythonOperator(
        task_id='print_gitsync_message',
        python_callable=print_gitsync_message,
    )

    bash_confirm = BashOperator(
        task_id='bash_confirm',
        bash_command='''
            echo "============================================================"
            echo "🚀 OUTPUT IS FROM GITSYNC!"
            echo "============================================================"
            echo "Synced from: GitHub Repository"
            echo "Current Time: $(date)"
            echo "Hostname: $(hostname)"
            echo "============================================================"
        ''',
    )

    print_message >> bash_confirm

