"""Tool: Analyze Excel column schema and map to semantic fields."""

# Known semantic field mappings for common Chinese/English HR column names
_KNOWN_MAPPINGS = {
    # Chinese
    "姓名": "name", "名字": "name", "员工姓名": "name",
    "工号": "employee_id", "员工编号": "employee_id", "编号": "employee_id",
    "部门": "department", "所属部门": "department", "部门名称": "department",
    "职位": "position", "岗位": "position", "职务": "position", "岗位名称": "position",
    "学历": "education", "最高学历": "education", "学历水平": "education",
    "年龄": "age",
    "性别": "gender",
    "工龄": "years_of_experience", "工作年限": "years_of_experience", "经验": "years_of_experience",
    "入职日期": "hire_date", "入职时间": "hire_date",
    "薪资": "salary", "工资": "salary", "月薪": "salary", "薪酬": "salary",
    "手机": "phone", "电话": "phone", "联系电话": "phone", "手机号": "phone",
    "邮箱": "email", "电子邮箱": "email",
    "技能": "skills", "专业技能": "skills",
    "专业": "major", "所学专业": "major",
    "学校": "university", "毕业院校": "university",
    "籍贯": "hometown", "户籍": "hometown",
    "地址": "address", "住址": "address", "居住地": "address",
    "状态": "status", "在职状态": "status",
    "生日": "birthday", "出生日期": "birthday",
    # English
    "name": "name", "full name": "name", "employee name": "name",
    "id": "employee_id", "employee id": "employee_id", "emp id": "employee_id",
    "department": "department", "dept": "department",
    "position": "position", "title": "position", "job title": "position", "role": "position",
    "education": "education", "degree": "education",
    "age": "age",
    "gender": "gender", "sex": "gender",
    "experience": "years_of_experience", "years of experience": "years_of_experience",
    "hire date": "hire_date", "join date": "hire_date", "start date": "hire_date",
    "salary": "salary", "pay": "salary",
    "phone": "phone", "mobile": "phone",
    "email": "email",
    "skills": "skills",
    "major": "major",
    "university": "university", "school": "university",
    "address": "address", "location": "address",
    "status": "status",
}


def analyze_schema(columns: list, sample_rows: list) -> dict:
    """Analyze column names and sample data to produce a semantic mapping.

    Args:
        columns: List of original column names from the Excel file.
        sample_rows: First few rows of data (list of dicts).

    Returns:
        dict with:
          - column_mapping: {original_col: semantic_field}
          - unmapped_columns: columns that couldn't be auto-mapped
          - field_types: inferred data types for each column
    """
    column_mapping = {}
    unmapped = []

    for col in columns:
        normalized = col.strip().lower()
        if normalized in _KNOWN_MAPPINGS:
            column_mapping[col] = _KNOWN_MAPPINGS[normalized]
        else:
            # Try partial matching
            matched = False
            for key, semantic in _KNOWN_MAPPINGS.items():
                if key in normalized or normalized in key:
                    column_mapping[col] = semantic
                    matched = True
                    break
            if not matched:
                unmapped.append(col)
                column_mapping[col] = col  # keep original name

    # Infer field types from sample data
    field_types = {}
    for col in columns:
        values = [row.get(col) for row in sample_rows if row.get(col) is not None]
        if not values:
            field_types[col] = "unknown"
        elif all(isinstance(v, (int, float)) for v in values):
            field_types[col] = "number"
        elif all(isinstance(v, str) and "T" in v and "-" in v for v in values):
            field_types[col] = "datetime"
        else:
            field_types[col] = "text"

    return {
        "column_mapping": column_mapping,
        "unmapped_columns": unmapped,
        "field_types": field_types,
    }
