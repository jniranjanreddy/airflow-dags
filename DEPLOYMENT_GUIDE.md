# Airflow DAGs Deployment Guide for AKS

This guide provides comprehensive instructions for deploying Apache Airflow DAGs to Azure Kubernetes Service (AKS).

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Deployment Methods](#deployment-methods)
3. [Method 1: Git-Sync (Recommended)](#method-1-git-sync-recommended)
4. [Method 2: Azure Blob Storage](#method-2-azure-blob-storage)
5. [Method 3: Persistent Volume](#method-3-persistent-volume)
6. [Method 4: Custom Docker Image](#method-4-custom-docker-image)
7. [Testing Your Deployment](#testing-your-deployment)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
- Azure CLI installed and configured
- kubectl configured to connect to your AKS cluster
- Helm 3.x installed
- Git configured with your credentials

### AKS Cluster Requirements
- Running AKS cluster
- kubectl access to the cluster
- Namespace for Airflow (default: `airflow`)

### Verify Prerequisites
```bash
# Check Azure CLI
az --version

# Verify AKS connection
kubectl get nodes

# Check Helm installation
helm version

# Verify namespace
kubectl get namespace airflow || kubectl create namespace airflow
```

---

## Deployment Methods

### Comparison of Methods

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **Git-Sync** | ✅ Automatic sync<br>✅ Version control<br>✅ Easy rollback | ⚠️ Requires Git repo<br>⚠️ Sync delay | Production, Team environments |
| **Azure Blob** | ✅ Cloud-native<br>✅ Scalable<br>✅ Cost-effective | ⚠️ Manual sync needed<br>⚠️ Additional setup | Large-scale deployments |
| **Persistent Volume** | ✅ Simple<br>✅ Fast access | ⚠️ Manual deployment<br>⚠️ No version control | Development, Testing |
| **Custom Image** | ✅ Immutable<br>✅ Fast startup | ⚠️ Rebuild required<br>⚠️ Large images | CI/CD pipelines |

---

## Method 1: Git-Sync (Recommended)

Git-sync automatically synchronizes DAGs from your Git repository to Airflow pods.

### Step 1: Push Your DAGs to Git Repository

```bash
# Initialize repository (if not already done)
git init
git add dags/
git commit -m "Add Airflow DAGs"

# Push to remote repository
git remote add origin https://github.com/YOUR_USERNAME/airflow-dags-repo.git
git push -u origin main
```

### Step 2: Configure Git Credentials (for Private Repos)

#### Option A: Using Personal Access Token (HTTPS)

```bash
# Create Kubernetes secret with Git credentials
kubectl create secret generic git-credentials \
  --from-literal=username=YOUR_GITHUB_USERNAME \
  --from-literal=password=YOUR_PERSONAL_ACCESS_TOKEN \
  --namespace airflow
```

#### Option B: Using SSH Key

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t rsa -b 4096 -C "airflow@yourdomain.com" -f ~/.ssh/airflow_rsa

# Add public key to your Git repository (GitHub/GitLab/Azure DevOps)
# Then create Kubernetes secret
kubectl create secret generic airflow-ssh-secret \
  --from-file=gitSshKey=$HOME/.ssh/airflow_rsa \
  --namespace airflow
```

### Step 3: Update Helm Values

Edit `airflow-values.yaml` and update the Git repository URL:

```yaml
dags:
  gitSync:
    enabled: true
    repo: https://github.com/YOUR_USERNAME/airflow-dags-repo.git
    branch: main
    subPath: "dags"
    
    # For private repos with HTTPS:
    credentialsSecret: git-credentials
    
    # For private repos with SSH:
    # repo: git@github.com:YOUR_USERNAME/airflow-dags-repo.git
    # sshKeySecret: airflow-ssh-secret
```

### Step 4: Install/Upgrade Airflow with Helm

```bash
# Add Apache Airflow Helm repository
helm repo add apache-airflow https://airflow.apache.org
helm repo update

# Install Airflow (first time)
helm install airflow apache-airflow/airflow \
  --namespace airflow \
  --values airflow-values.yaml \
  --create-namespace

# OR upgrade existing installation
helm upgrade airflow apache-airflow/airflow \
  --namespace airflow \
  --values airflow-values.yaml
```

### Step 5: Verify Git-Sync is Working

```bash
# Check git-sync logs
kubectl logs -n airflow -l component=scheduler -c git-sync --tail=50

# You should see logs like:
# INFO: synced abcd1234 (1 files changed)
```

### Step 6: Access Airflow UI

```bash
# Get the LoadBalancer IP (if using LoadBalancer service type)
kubectl get svc -n airflow airflow-webserver

# Or use port-forward for testing
kubectl port-forward svc/airflow-webserver 8080:8080 -n airflow

# Access at: http://localhost:8080
# Default credentials: admin / admin
```

---

## Method 2: Azure Blob Storage

Use Azure Blob Storage for DAG storage (requires custom configuration).

### Step 1: Create Azure Storage Account

```bash
# Variables
RESOURCE_GROUP="airflow-rg"
STORAGE_ACCOUNT="airflowdags$(date +%s)"
CONTAINER_NAME="dags"
LOCATION="eastus"

# Create storage account
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS

# Create blob container
az storage container create \
  --name $CONTAINER_NAME \
  --account-name $STORAGE_ACCOUNT
```

### Step 2: Upload DAGs to Blob Storage

```bash
# Get connection string
AZURE_STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --query connectionString -o tsv)

# Upload DAGs
az storage blob upload-batch \
  --destination $CONTAINER_NAME \
  --source ./dags \
  --connection-string $AZURE_STORAGE_CONNECTION_STRING
```

### Step 3: Configure Airflow

```yaml
# In airflow-values.yaml
airflow:
  config:
    AIRFLOW__CORE__DAGS_FOLDER: /opt/airflow/dags
    
env:
  - name: AZURE_STORAGE_CONNECTION_STRING
    valueFrom:
      secretKeyRef:
        name: azure-storage-secret
        key: connection-string

# Add sidecar container for blob sync (custom implementation needed)
```

### Step 4: Create Sync Script

You'll need to implement a custom sync mechanism or use Azure Files with SMB mounting.

---

## Method 3: Persistent Volume

Use Azure Disk or Azure Files for DAG storage.

### Step 1: Create Persistent Volume Claim

Create `dags-pvc.yaml`:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: airflow-dags-pvc
  namespace: airflow
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: azurefile  # Use Azure Files for ReadWriteMany
  resources:
    requests:
      storage: 5Gi
```

```bash
kubectl apply -f dags-pvc.yaml
```

### Step 2: Update Helm Values

```yaml
# In airflow-values.yaml
dags:
  persistence:
    enabled: true
    existingClaim: airflow-dags-pvc
  gitSync:
    enabled: false
```

### Step 3: Copy DAGs to PVC

```bash
# Create a temporary pod to copy DAGs
kubectl run -i --tty --rm debug --image=busybox --restart=Never \
  --overrides='
{
  "spec": {
    "containers": [
      {
        "name": "debug",
        "image": "busybox",
        "stdin": true,
        "tty": true,
        "volumeMounts": [{
          "mountPath": "/dags",
          "name": "dags-volume"
        }]
      }
    ],
    "volumes": [{
      "name": "dags-volume",
      "persistentVolumeClaim": {
        "claimName": "airflow-dags-pvc"
      }
    }]
  }
}' -- sh

# Then from your local machine:
kubectl cp ./dags/. airflow/$(kubectl get pod -n airflow -l component=scheduler -o jsonpath='{.items[0].metadata.name}'):/opt/airflow/dags/
```

---

## Method 4: Custom Docker Image

Build a custom Airflow image with DAGs baked in.

### Step 1: Create Dockerfile

Create `Dockerfile`:

```dockerfile
FROM apache/airflow:2.7.3-python3.10

# Copy DAGs
COPY dags/ ${AIRFLOW_HOME}/dags/

# Install additional Python packages (if needed)
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Set ownership
USER airflow
```

### Step 2: Build and Push Image

```bash
# Build image
docker build -t youracr.azurecr.io/airflow-custom:latest .

# Login to Azure Container Registry
az acr login --name youracr

# Push image
docker push youracr.azurecr.io/airflow-custom:latest
```

### Step 3: Update Helm Values

```yaml
# In airflow-values.yaml
images:
  airflow:
    repository: youracr.azurecr.io/airflow-custom
    tag: latest

dags:
  gitSync:
    enabled: false
```

---

## Testing Your Deployment

### 1. Verify Pods are Running

```bash
kubectl get pods -n airflow

# Expected output:
# NAME                                    READY   STATUS    RESTARTS   AGE
# airflow-scheduler-xxx                   2/2     Running   0          5m
# airflow-webserver-xxx                   1/1     Running   0          5m
# airflow-postgresql-0                    1/1     Running   0          5m
```

### 2. Check Scheduler Logs

```bash
kubectl logs -n airflow -l component=scheduler -c scheduler --tail=100
```

### 3. Verify DAGs are Loaded

```bash
# Access Airflow UI and check DAGs page
# Or use Airflow CLI
kubectl exec -n airflow -it deploy/airflow-scheduler -- airflow dags list
```

### 4. Test Example DAG

```bash
# Trigger the example DAG
kubectl exec -n airflow -it deploy/airflow-scheduler -- \
  airflow dags trigger example_aks_dag

# Check DAG run status
kubectl exec -n airflow -it deploy/airflow-scheduler -- \
  airflow dags list-runs -d example_aks_dag
```

---

## Troubleshooting

### DAGs Not Appearing in UI

**Check git-sync logs:**
```bash
kubectl logs -n airflow -l component=scheduler -c git-sync
```

**Verify Git repository access:**
```bash
kubectl exec -n airflow -it deploy/airflow-scheduler -c git-sync -- \
  ls -la /opt/airflow/dags
```

**Check scheduler logs for import errors:**
```bash
kubectl logs -n airflow -l component=scheduler -c scheduler | grep -i error
```

### Git-Sync Authentication Issues

**Test credentials:**
```bash
# For HTTPS
kubectl get secret git-credentials -n airflow -o yaml

# For SSH
kubectl get secret airflow-ssh-secret -n airflow -o yaml
```

### Performance Issues

**Increase resources:**
```yaml
scheduler:
  resources:
    limits:
      cpu: 2000m
      memory: 4Gi
```

**Reduce git-sync interval:**
```yaml
dags:
  gitSync:
    wait: 300  # Sync every 5 minutes instead of 60 seconds
```

### Pod Crashes

**Check events:**
```bash
kubectl get events -n airflow --sort-by='.lastTimestamp'
```

**Describe pod:**
```bash
kubectl describe pod -n airflow -l component=scheduler
```

### Database Connection Issues

**Verify PostgreSQL:**
```bash
kubectl logs -n airflow airflow-postgresql-0
kubectl exec -n airflow -it airflow-postgresql-0 -- psql -U airflow
```

---

## Best Practices

1. **Use Git-Sync for Production**: Provides version control and automatic updates
2. **Implement CI/CD**: Automate DAG testing before deployment
3. **Use Separate Branches**: Use dev/staging/prod branches for different environments
4. **Monitor Resource Usage**: Set appropriate resource limits and requests
5. **Enable Logging**: Use Azure Log Analytics or ELK stack
6. **Backup Database**: Regular backups of PostgreSQL metadata database
7. **Use Secrets Manager**: Store sensitive data in Azure Key Vault
8. **Implement RBAC**: Configure proper role-based access control
9. **Use Ingress with TLS**: Secure Airflow UI with HTTPS
10. **Set Up Alerts**: Monitor DAG failures and system health

---

## Additional Resources

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Airflow Helm Chart](https://airflow.apache.org/docs/helm-chart/stable/index.html)
- [AKS Documentation](https://docs.microsoft.com/en-us/azure/aks/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

---

## Support

For issues and questions:
- Check Airflow logs: `kubectl logs -n airflow <pod-name>`
- Review Kubernetes events: `kubectl get events -n airflow`
- Consult official documentation
- Check GitHub issues for Airflow Helm Chart

---

**Last Updated**: October 2025
**Airflow Version**: 2.7.3
**Helm Chart Version**: 1.11.0

