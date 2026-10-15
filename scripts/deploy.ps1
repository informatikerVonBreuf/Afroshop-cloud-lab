# Script PowerShell pour déployer AfroShop Cloud AI Guard sur Google Cloud Run

$PROJECT_ID = "Afroshop-cloud-lab"
$REGION = "europe-west1"
$SERVICE_NAME = "afroshop-guard"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " DÉPLOIEMENT AFROSHOP GUARD SUR GOOGLE CLOUD RUN" -ForegroundColor Cyan
Write-Host " Projet GCP : $PROJECT_ID | Région : $REGION" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Vérifier si gcloud est installé
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Le Google Cloud CLI (gcloud) n'est pas encore installé sur votre machine." -ForegroundColor Yellow
    Write-Host "Pour déployer sans installer gcloud en local, vous pouvez :" -ForegroundColor Yellow
    Write-Host "1. Pousser ce projet sur GitHub." -ForegroundColor White
    Write-Host "2. Ouvrir Google Cloud Shell (dans la console GCP) et exécuter :" -ForegroundColor White
    Write-Host "   git clone <URL_DU_REPO> ; cd Afroshop-cloud-lab" -ForegroundColor Green
    Write-Host "   gcloud run deploy afroshop-guard --source . --region europe-west1 --allow-unauthenticated" -ForegroundColor Green
    exit
}

Write-Host "[1/3] Configuration du projet courant..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID

Write-Host "[2/3] Activation des APIs nécessaires (Cloud Run, Cloud Build, Cloud Logging)..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com cloudbuild.googleapis.com logging.googleapis.com --project=$PROJECT_ID

Write-Host "[3/3] Déploiement de l'application conteneurisée..." -ForegroundColor Yellow
gcloud run deploy $SERVICE_NAME `
    --source . `
    --region $REGION `
    --allow-unauthenticated `
    --project $PROJECT_ID

Write-Host " Déploiement terminé avec succès !" -ForegroundColor Green
