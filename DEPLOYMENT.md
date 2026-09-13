# Deployment Guide: Azure (Backend) & Vercel (Frontend)

This guide walks you through deploying the `HirePrep_AI` platform using your $100 Azure Student plan for the backend and Vercel for the frontend.

## 1. Deploying the Backend (Azure App Service)

Since you are using the Azure Student Plan, **Azure App Service (Web App for Containers)** or **Azure Container Apps** are your best options. Both fully support the provided `Dockerfile`.

### Option A: Deploy via Azure CLI (Recommended)

1. **Install the Azure CLI** on your local machine and log in:
   ```bash
   az login
   ```
2. **Create a Resource Group:**
   ```bash
   az group create --name HirePrep-RG --location eastus
   ```
3. **Create an Azure Container Registry (ACR) & Build Image:**
   ```bash
   az acr create --resource-group HirePrep-RG --name hireprepacr --sku Basic
   az acr build --registry hireprepacr --image hireprep-backend:latest ./backend
   ```
4. **Create the App Service Plan (Free or B1 Linux):**
   ```bash
   az appservice plan create --name HirePrep-Plan --resource-group HirePrep-RG --sku B1 --is-linux
   ```
5. **Create the Web App and deploy the container:**
   ```bash
   az webapp create --resource-group HirePrep-RG --plan HirePrep-Plan --name hireprep-backend-api --deployment-container-image-name hireprepacr.azurecr.io/hireprep-backend:latest
   ```
6. **Configure Environment Variables in Azure:**
   Go to the Azure Portal > App Services > `hireprep-backend-api` > **Settings > Environment variables**. Add all the keys from your `.env` file (e.g., `GROQ_API_KEY`, `TAVILY_API_KEY`, etc.). Also set `WEBSITES_PORT=8000`.

*Note: The backend URL will be `https://hireprep-backend-api.azurewebsites.net`.*

### Database Note
By default, SQLite databases (`hireprep.db`) are ephemeral in containers. To persist interview data across container restarts, you should configure the backend to use your **Supabase PostgreSQL database** instead of SQLite by updating your SQLAlchemy connection string environment variable in Azure.

---

## 2. Deploying the Frontend (Vercel)

Vercel is incredibly fast and free for frontend hosting. The repository is already configured with `vercel.json` for React Router support.

1. Go to [Vercel](https://vercel.com/) and log in with your GitHub account.
2. Click **Add New > Project**.
3. Import the `HirePrep_AI` repository from your GitHub.
4. **Configure the Project:**
   - **Framework Preset:** Vite
   - **Root Directory:** Edit this and select `frontend`
5. **Set Environment Variables:**
   Expand the "Environment Variables" section and add:
   - `VITE_SUPABASE_URL` = (Your Supabase URL)
   - `VITE_SUPABASE_ANON_KEY` = (Your Supabase Anon Key)
   - `VITE_API_URL` = `https://hireprep-backend-api.azurewebsites.net` *(The URL from your Azure deployment)*
6. Click **Deploy**.

Vercel will build the frontend and provide you with a live URL (e.g., `https://hireprep-ai.vercel.app`).

## 3. CORS Configuration

Once both are deployed, ensure your backend allows requests from your Vercel URL.
In your backend's `app/main.py`, make sure the CORS configuration allows your Vercel URL:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://hireprep-ai.vercel.app", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Commit this change and redeploy the backend if necessary. Your app is now live!
