with open("backend/app/api/v1/router.py", "r") as f:
    content = f.read()

import re
if "parents_router" not in content:
    content = re.sub(r"from app\.api\.v1\.students import router as students_router", 
                     "from app.api.v1.students import router as students_router\nfrom app.api.v1.parents import router as parents_router", content)
    content = re.sub(r"api_v1_router\.include_router\(students_router\)", 
                     "api_v1_router.include_router(students_router)\napi_v1_router.include_router(parents_router)", content)

with open("backend/app/api/v1/router.py", "w") as f:
    f.write(content)
