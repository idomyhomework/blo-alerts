1. ## Instalar prerequisitos

Docker Desktop → https://www.docker.com/products/docker-desktop/
Git → https://git-scm.com/download/win

2. ## Clonar el repositorio
   ```bash
   git clone https://github.com/idomyhomework/blo-alerts
   ```
   ```bash
   cd blo-alerts
   ```
3. ## Crear su .env local
   - copia .env.example a .env
   - Luego abre .env y cambia las contraseñas por las que quiera usar en local.
4. ## Arrancar el proyecto

   ```bash
   docker compose up -d
   ```

5. ## Aplicar las migraciones
   ```bash
   docker compose exec api alembic upgrade head
   ```
6. ## Verificar que funciona
   - 1. http://localhost:8000/healthz → {"status": "ok"}
   - 2. http://localhost:8000/docs → Swagger UI
