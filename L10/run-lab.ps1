# Запускати у PowerShell з установленим і запущеним Docker-сумісним runtime.
$ErrorActionPreference = "Stop"

docker pull nginxdemos/hello
if ($LASTEXITCODE -ne 0) { throw "Не вдалося завантажити образ" }

# Прибираємо попередній контейнер з тим самим ім'ям, якщо він є.
$existing = docker ps -a --filter "name=^hello-web$" --format "{{.Names}}"
if ($existing -eq "hello-web") {
    docker rm -f hello-web
    if ($LASTEXITCODE -ne 0) { throw "Не вдалося видалити старий контейнер" }
}

docker run -d --name hello-web -p 8080:80 nginxdemos/hello
if ($LASTEXITCODE -ne 0) { throw "Не вдалося запустити контейнер" }

Write-Host "`n--- docker ps ---"
docker ps
Write-Host "`n--- docker images ---"
docker images
Write-Host "`n--- HTTP response ---"
curl.exe -I http://localhost:8080
Write-Host "`n--- logs ---"
docker logs hello-web

Write-Host "`nПеревірка завершена. Для зупинки: docker stop hello-web"
Write-Host "Для видалення: docker rm hello-web"
