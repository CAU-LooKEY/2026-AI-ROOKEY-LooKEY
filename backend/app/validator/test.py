from app.validator.collect_cases import load_case_from_file
from app.validator.rules import validate_and_attach
import json

case = load_case_from_file("app/validator/sample_cases/kexaone_result_001.json")
result = validate_and_attach(case)
print(json.dumps(result["validationResults"], ensure_ascii=False, indent=2))