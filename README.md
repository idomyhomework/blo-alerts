1. **Instalar prerequisitos**

Docker Desktop → https://www.docker.com/products/docker-desktop/
Git → https://git-scm.com/download/win

2. **Clonar el repositorio**
   bashgit clone https://github.com/tu-usuario/tu-repo.git
   cd tu-repo

3. **Crear su .env local**
   bashcopy .env.example .env
   Luego abre .env y cambia las contraseñas por las que quiera usar en local.

4. **Arrancar el proyecto**
   bashdocker compose up -d

5. **Aplicar las migraciones**
   bashdocker compose exec api alembic upgrade head

6. **Verificar que funciona**

http://localhost:8000/healthz → {"status": "ok"}
http://localhost:8000/docs → Swagger UI
