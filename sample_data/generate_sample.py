"""Generate a sample HR roster Excel file for testing."""

import random
from openpyxl import Workbook

DEPARTMENTS = ["技术部", "市场部", "销售部", "人力资源部", "财务部", "产品部", "运营部"]
POSITIONS = {
    "技术部": ["高级工程师", "中级工程师", "初级工程师", "技术总监", "架构师"],
    "市场部": ["市场经理", "市场专员", "品牌主管", "数字营销经理"],
    "销售部": ["销售经理", "销售代表", "大客户经理", "区域总监"],
    "人力资源部": ["HR经理", "招聘专员", "培训主管", "HRBP"],
    "财务部": ["财务经理", "会计", "出纳", "审计专员"],
    "产品部": ["产品经理", "高级产品经理", "产品总监", "产品助理"],
    "运营部": ["运营经理", "运营专员", "数据分析师", "用户运营"],
}
EDUCATIONS = ["大专", "本科", "硕士", "博士"]
EDUCATION_WEIGHTS = [0.15, 0.50, 0.30, 0.05]
SKILLS_POOL = {
    "技术部": ["Python", "Java", "Go", "Kubernetes", "AWS", "React", "SQL", "机器学习", "微服务", "DevOps"],
    "市场部": ["SEO", "SEM", "内容营销", "社交媒体", "数据分析", "品牌策划"],
    "销售部": ["客户关系管理", "谈判", "渠道拓展", "B2B销售", "方案营销"],
    "人力资源部": ["招聘", "绩效管理", "薪酬设计", "劳动法", "组织发展"],
    "财务部": ["财务分析", "税务筹划", "成本控制", "Excel", "ERP"],
    "产品部": ["用户研究", "需求分析", "Axure", "数据驱动", "竞品分析"],
    "运营部": ["数据分析", "用户增长", "活动策划", "SQL", "A/B测试"],
}
SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜")
GIVEN_NAMES = list("伟芳娜敏静丽强磊洋艺勇毅俊峰飞华明雪慧婷超杰建军平刚辉斌鹏")
STATUSES = ["在职", "在职", "在职", "在职", "离职", "试用期"]

random.seed(42)


def random_name():
    return random.choice(SURNAMES) + "".join(random.choices(GIVEN_NAMES, k=random.choice([1, 2])))


def generate_sample_roster(filepath: str, num_employees: int = 80):
    wb = Workbook()
    ws = wb.active
    ws.title = "员工花名册"

    headers = ["工号", "姓名", "性别", "年龄", "部门", "职位", "学历", "专业",
               "工作年限", "月薪(元)", "技能", "入职日期", "联系电话", "邮箱", "在职状态"]
    ws.append(headers)

    majors = ["计算机科学", "软件工程", "信息管理", "市场营销", "金融学", "会计学",
              "人力资源管理", "工商管理", "电子商务", "数据科学", "统计学", "英语"]

    for i in range(1, num_employees + 1):
        dept = random.choice(DEPARTMENTS)
        position = random.choice(POSITIONS[dept])
        edu = random.choices(EDUCATIONS, weights=EDUCATION_WEIGHTS, k=1)[0]
        age = random.randint(22, 50)
        experience = max(0, age - random.randint(22, 26))
        base_salary = random.randint(8000, 50000)
        gender = random.choice(["男", "女"])
        skills = ", ".join(random.sample(SKILLS_POOL[dept], k=min(3, len(SKILLS_POOL[dept]))))
        year = random.randint(2015, 2025)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        phone = f"1{random.choice(['38','39','58','59','88','89'])}{random.randint(10000000, 99999999)}"

        name = random_name()
        email = f"employee{i:03d}@example.com"

        ws.append([
            f"EMP{i:04d}",
            name,
            gender,
            age,
            dept,
            position,
            edu,
            random.choice(majors),
            experience,
            base_salary,
            skills,
            f"{year}-{month:02d}-{day:02d}",
            phone,
            email,
            random.choice(STATUSES),
        ])

    # Adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 30)

    wb.save(filepath)
    print(f"Sample roster generated: {filepath} ({num_employees} employees)")


if __name__ == "__main__":
    generate_sample_roster("sample_data/sample_roster.xlsx")
