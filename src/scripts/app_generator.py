"""
Application Generator from Boilerplate Graph

This script:
1. Queries Neo4j for components needed for an app type
2. Resolves component dependencies
3. Generates project structure
4. Writes code files
5. Creates configuration files
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import uuid4

from src.neo4j_client import Neo4jClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AppGenerator:
    """Generate complete applications from boilerplate components"""

    def __init__(self, client: Neo4jClient, app_type: str, output_dir: Path):
        self.client = client
        self.app_type = app_type
        self.output_dir = output_dir
        self.components: Dict[str, Dict] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self.project_structure = {
            "backend": {
                "src": {
                    "models": [],
                    "services": [],
                    "routers": [],
                    "middleware": [],
                    "schemas": [],
                },
                "tests": [],
                "migrations": [],
            },
            "frontend": {
                "src": {
                    "components": [],
                    "pages": [],
                    "hooks": [],
                    "services": [],
                    "types": [],
                },
            },
        }

    async def fetch_components(self) -> bool:
        """Fetch all components needed for this app type"""
        logger.info(f"🔍 Fetching components for {self.app_type}...")

        try:
            async with self.client.driver.session() as session:
                # Get app-specific components
                result = await session.run(
                    """
                    MATCH (c:Component)
                    WHERE c.purpose CONTAINS $app_type OR c.purpose CONTAINS 'shared'
                    RETURN c.id as id, c.name as name, c.description as description,
                           c.category as category, c.code as code, c.language as language,
                           c.framework as framework
                    """,
                    app_type=self.app_type
                )

                records = await result.fetch(100)
                for record in records:
                    comp_id = record["id"]
                    self.components[comp_id] = {
                        "id": comp_id,
                        "name": record["name"],
                        "description": record["description"],
                        "category": record["category"],
                        "code": record["code"],
                        "language": record["language"],
                        "framework": record["framework"],
                    }

            logger.info(f"✅ Fetched {len(self.components)} components")
            return len(self.components) > 0

        except Exception as e:
            logger.error(f"❌ Failed to fetch components: {e}")
            return False

    async def resolve_dependencies(self) -> bool:
        """Resolve component dependencies"""
        logger.info("🔗 Resolving dependencies...")

        try:
            async with self.client.driver.session() as session:
                for comp_id in self.components.keys():
                    result = await session.run(
                        """
                        MATCH (c:Component {id: $comp_id})
                        OPTIONAL MATCH (c)-[r:USES|EXTENDS|REQUIRES]->(dep:Component)
                        RETURN COLLECT(dep.id) as dependencies
                        """,
                        comp_id=comp_id
                    )

                    record = await result.single()
                    if record:
                        deps = record["dependencies"]
                        self.dependencies[comp_id] = [d for d in deps if d in self.components]

            logger.info(f"✅ Resolved dependencies for {len(self.dependencies)} components")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to resolve dependencies: {e}")
            return False

    def create_project_structure(self) -> bool:
        """Create project directory structure"""
        logger.info(f"📁 Creating project structure in {self.output_dir}...")

        try:
            # Create base directories
            (self.output_dir / "backend" / "src" / "models").mkdir(parents=True, exist_ok=True)
            (self.output_dir / "backend" / "src" / "services").mkdir(parents=True, exist_ok=True)
            (self.output_dir / "backend" / "src" / "routers").mkdir(parents=True, exist_ok=True)
            (self.output_dir / "backend" / "src" / "middleware").mkdir(parents=True, exist_ok=True)
            (self.output_dir / "backend" / "src" / "schemas").mkdir(parents=True, exist_ok=True)
            (self.output_dir / "backend" / "tests").mkdir(parents=True, exist_ok=True)

            (self.output_dir / "frontend" / "src" / "components").mkdir(parents=True, exist_ok=True)
            (self.output_dir / "frontend" / "src" / "pages").mkdir(parents=True, exist_ok=True)
            (self.output_dir / "frontend" / "src" / "hooks").mkdir(parents=True, exist_ok=True)
            (self.output_dir / "frontend" / "src" / "services").mkdir(parents=True, exist_ok=True)

            logger.info("✅ Project structure created")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create project structure: {e}")
            return False

    def write_component_files(self) -> bool:
        """Write component code to files"""
        logger.info("✏️ Writing component files...")

        try:
            for comp_id, comp_data in self.components.items():
                category = comp_data["category"]
                language = comp_data["language"]
                name = comp_data["name"]
                code = comp_data["code"]

                # Determine file path based on category
                if category == "Entity":
                    subdir = "models"
                elif category == "Service":
                    subdir = "services"
                elif category == "API":
                    subdir = "routers"
                elif category == "Middleware":
                    subdir = "middleware"
                else:
                    subdir = "services"

                # Create filename
                filename = f"{comp_id}.py"  # Assuming Python for now
                filepath = self.output_dir / "backend" / "src" / subdir / filename

                # Write file
                with open(filepath, "w") as f:
                    f.write(f"# {name}\n")
                    f.write(f"# {comp_data['description']}\n\n")
                    f.write(code)

            logger.info(f"✅ Wrote {len(self.components)} component files")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to write component files: {e}")
            return False

    def create_config_files(self) -> bool:
        """Create configuration files"""
        logger.info("⚙️ Creating configuration files...")

        try:
            # Backend .env
            env_content = """
ENVIRONMENT=development
DATABASE_URL=postgresql://user:password@localhost:5432/app_db
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
"""
            with open(self.output_dir / "backend" / ".env", "w") as f:
                f.write(env_content)

            # Backend pyproject.toml / requirements.txt
            requirements = """
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose==3.3.0
bcrypt==4.1.1
pytest==7.4.3
httpx==0.25.1
"""
            with open(self.output_dir / "backend" / "requirements.txt", "w") as f:
                f.write(requirements)

            # Frontend package.json (basic)
            package_json = """
{
  "name": "frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.2"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.8"
  }
}
"""
            with open(self.output_dir / "frontend" / "package.json", "w") as f:
                f.write(package_json)

            logger.info("✅ Created configuration files")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create config files: {e}")
            return False

    def create_main_files(self) -> bool:
        """Create main application files"""
        logger.info("🚀 Creating main application files...")

        try:
            # Backend main.py
            main_py = f"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="{self.app_type.replace('_', ' ').title()}",
    description="Generated from boilerplate",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {{"message": "Welcome to {self.app_type}"}}

@app.get("/health")
async def health():
    return {{"status": "ok"}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
            with open(self.output_dir / "backend" / "src" / "main.py", "w") as f:
                f.write(main_py)

            # Frontend App.tsx/jsx
            app_jsx = """
import React from 'react'

function App() {
  return (
    <div className="app">
      <h1>Welcome</h1>
      <p>Application generated from boilerplate</p>
    </div>
  )
}

export default App
"""
            with open(self.output_dir / "frontend" / "src" / "App.jsx", "w") as f:
                f.write(app_jsx)

            logger.info("✅ Created main application files")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create main files: {e}")
            return False

    def create_readme(self) -> bool:
        """Create README with setup instructions"""
        logger.info("📝 Creating README...")

        try:
            readme = f"""# {self.app_type.replace('_', ' ').title()}

Generated from boilerplate template.

## Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
.
├── backend/
│   ├── src/
│   │   ├── models/          # Database models
│   │   ├── services/        # Business logic
│   │   ├── routers/         # API endpoints
│   │   ├── middleware/      # Request/response middleware
│   │   └── main.py          # Application entry point
│   ├── tests/               # Test suite
│   └── requirements.txt     # Python dependencies
└── frontend/
    ├── src/
    │   ├── components/      # React components
    │   ├── pages/           # Page components
    │   ├── hooks/           # Custom hooks
    │   └── App.jsx          # Root component
    └── package.json         # NPM dependencies
```

## Features

- Generated from boilerplate components
- FastAPI backend
- React frontend
- SQLAlchemy ORM
- JWT authentication
- CORS enabled

## Generated Components

"""
            readme += f"\n### Included Components ({len(self.components)})\n\n"
            for comp_id, comp_data in sorted(self.components.items()):
                readme += f"- **{comp_data['name']}** ({comp_data['category']}): {comp_data['description']}\n"

            with open(self.output_dir / "README.md", "w") as f:
                f.write(readme)

            logger.info("✅ Created README")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create README: {e}")
            return False

    async def generate(self) -> bool:
        """Generate complete application"""
        logger.info(f"\n🚀 GENERATING {self.app_type.upper()} APPLICATION\n")

        steps = [
            ("Fetching components", self.fetch_components),
            ("Resolving dependencies", self.resolve_dependencies),
            ("Creating project structure", self.create_project_structure),
            ("Writing component files", self.write_component_files),
            ("Creating configuration files", self.create_config_files),
            ("Creating main application files", self.create_main_files),
            ("Creating README", self.create_readme),
        ]

        all_success = True
        for step_name, step_func in steps:
            # Call async or sync functions appropriately
            if asyncio.iscoroutinefunction(step_func):
                step_result = await step_func()
            else:
                step_result = step_func()

            if not step_result:
                logger.error(f"❌ {step_name} failed")
                all_success = False
                break

        if all_success:
            logger.info(f"\n✅ ✅ ✅ APPLICATION GENERATED SUCCESSFULLY ✅ ✅ ✅\n")
            logger.info(f"Location: {self.output_dir}")
            logger.info(f"Components: {len(self.components)}")
            logger.info(f"Dependencies: {sum(len(v) for v in self.dependencies.values())}\n")
        else:
            logger.error("\n❌ Application generation failed\n")

        return all_success


async def main():
    """Main application generation orchestrator"""
    client = Neo4jClient()

    try:
        if not await client.connect():
            logger.error("Failed to connect to Neo4j")
            return

        logger.info("✅ Connected to Neo4j\n")

        # Generate all three applications
        apps = [
            ("task_manager", Path("/tmp/generated/task_manager")),
            ("crm", Path("/tmp/generated/crm")),
            ("ecommerce", Path("/tmp/generated/ecommerce")),
        ]

        for app_type, output_dir in apps:
            generator = AppGenerator(client, app_type, output_dir)
            success = await generator.generate()
            if not success:
                logger.error(f"Failed to generate {app_type}")
                break
            await asyncio.sleep(1)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
