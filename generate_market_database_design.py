"""Generate Market_Database_Design.docx for the Market Stall Management System (market_db).

Usage:
    python generate_market_database_design.py

Requires:
    pip install python-docx

The document follows the required structure:
1. Title Page
2. Proposed System Description
3. Conceptual, Logical, and Physical Design (with Mermaid references)
4. List of Tables
5. Data Dictionary
6. Entity-Relationship Diagram (ERD) placeholder
7. Entity Description & Relationship Summary
8. SQL Statements: 30 SELECT, 10 INSERT, 10 UPDATE, 5 DELETE, 5 Subquery, 10 JOIN
"""

from datetime import date

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUTPUT_FILE = "Market_Database_Design.docx"
NAVY = RGBColor(0x1F, 0x3A, 0x5F)
DARK_GRAY = RGBColor(0x40, 0x40, 0x40)
LIGHT_BLUE = "D9E2F3"
LIGHT_GRAY = "F2F2F2"


# ---------------------------------------------------------------------------
# Low-level formatting helpers
# ---------------------------------------------------------------------------
def set_run_font(run, name="Times New Roman", size=None, bold=None, italic=None, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    rfonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def shade_cell(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_table_borders(table, val="single", size=8, color="7F7F7F"):
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), val)
        element.set(qn("w:sz"), str(size))
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)
        borders.append(element)
    tbl_pr.append(borders)


def set_table_fixed_layout(table):
    tbl_pr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)


def set_col_widths(table, widths):
    for row in table.rows:
        for index, width in enumerate(widths):
            row.cells[index].width = Inches(width)


def set_repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def prevent_row_split(row):
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))


def set_row_height(row, inches):
    tr_pr = row._tr.get_or_add_trPr()
    height = OxmlElement("w:trHeight")
    height.set(qn("w:val"), str(int(inches * 1440)))
    height.set(qn("w:hRule"), "atLeast")
    tr_pr.append(height)


def add_field(paragraph, instruction, size=9):
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(end)
    set_run_font(run, size=size)


def add_body(doc, text, lead=None):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.space_after = Pt(8)
    paragraph.paragraph_format.line_spacing = 1.5
    if lead:
        run = paragraph.add_run(lead)
        set_run_font(run, bold=True)
    run = paragraph.add_run(text)
    set_run_font(run)
    return paragraph


def add_caption(doc, text):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(8)
    run = paragraph.add_run(text)
    set_run_font(run, size=10, italic=True, color=DARK_GRAY)
    return paragraph


def add_code_block(doc, code, width=6.5):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_fixed_layout(table)
    set_table_borders(table, val="single", size=6, color="A6A6A6")
    cell = table.cell(0, 0)
    cell.width = Inches(width)
    shade_cell(cell, LIGHT_GRAY)
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    run = paragraph.add_run(code.strip())
    set_run_font(run, name="Consolas", size=9)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_placeholder_box(doc, label, height=2.6, note=None, dashed=True, width=6.5):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_fixed_layout(table)
    set_table_borders(
        table,
        val="dashed" if dashed else "single",
        size=10,
        color="808080",
    )
    row = table.rows[0]
    prevent_row_split(row)
    set_row_height(row, height)
    cell = row.cells[0]
    cell.width = Inches(width)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    shade_cell(cell, "FAFAFA")

    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(4)
    run = paragraph.add_run(label)
    set_run_font(run, size=11, bold=True, color=RGBColor(0x7F, 0x7F, 0x7F))

    if note:
        note_paragraph = cell.add_paragraph()
        note_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        note_run = note_paragraph.add_run(note)
        set_run_font(note_run, size=9, italic=True, color=RGBColor(0x99, 0x99, 0x99))

    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_formatted_table(doc, headers, rows, widths, font_size=9, header_fill=LIGHT_BLUE):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_fixed_layout(table)

    header_row = table.rows[0]
    set_repeat_header(header_row)
    prevent_row_split(header_row)
    for index, header in enumerate(headers):
        cell = header_row.cells[index]
        shade_cell(cell, header_fill)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        run = paragraph.add_run(header)
        set_run_font(run, size=font_size, bold=True)

    for values in rows:
        row = table.add_row()
        prevent_row_split(row)
        for index, value in enumerate(values):
            cell = row.cells[index]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.0
            run = paragraph.add_run(str(value))
            set_run_font(run, size=font_size)

    set_col_widths(table, widths)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_mermaid_reference(doc, title, code):
    heading = doc.add_paragraph()
    heading.paragraph_format.space_before = Pt(10)
    heading.paragraph_format.space_after = Pt(4)
    run = heading.add_run(title)
    set_run_font(run, size=11, bold=True, color=NAVY)
    add_body(
        doc,
        "The block below is the Mermaid.js erDiagram reference text for this design view. "
        "Paste it into a Mermaid live editor or keep it as the textual basis when recreating "
        "the diagram in draw.io.",
    )
    add_code_block(doc, code)


# ---------------------------------------------------------------------------
# Document data
# ---------------------------------------------------------------------------
TABLES = [
    {
        "name": "stalls_vendor",
        "description": "Master list of registered market vendors and their contact details.",
        "pk": "id",
        "fields": [
            ("id", "Unique identifier for each vendor record.", "BIGINT", "20",
             "PRIMARY KEY, AUTO_INCREMENT, NOT NULL"),
            ("name", "Full name of the vendor or business owner.", "VARCHAR", "100", "NOT NULL"),
            ("contact_number", "Primary mobile or telephone number of the vendor.", "VARCHAR", "20",
             "NOT NULL"),
            ("category", "Main product line or business category of the vendor.", "VARCHAR", "50",
             "NULL (optional)"),
        ],
    },
    {
        "name": "stalls_stall",
        "description": "Market stall records, including assignment, rent rate, and due dates.",
        "pk": "id",
        "fields": [
            ("id", "Unique identifier for each stall record.", "BIGINT", "20",
             "PRIMARY KEY, AUTO_INCREMENT, NOT NULL"),
            ("stall_number", "Official stall code or number displayed in the market.", "VARCHAR", "50",
             "UNIQUE, NOT NULL"),
            ("vendor_id", "Reference to the vendor currently assigned to the stall.", "BIGINT", "20",
             "FOREIGN KEY (stalls_vendor.id), NULL, ON DELETE SET NULL"),
            ("vendor_name", "Denormalized vendor name used for quick display and legacy records.",
             "VARCHAR", "100", "NULL"),
            ("category", "Stall or product category (for example, Vegetables, Meat, Fish).",
             "VARCHAR", "100", "NULL"),
            ("rent_rate", "Monthly rent charged for the stall.", "DECIMAL", "10,2",
             "NOT NULL, DEFAULT 0.00"),
            ("contact_number", "Contact number stored directly on the stall record.", "VARCHAR", "20",
             "NULL"),
            ("next_due_date", "Next scheduled rent due date for the stall.", "DATE", "—", "NULL"),
            ("date_paid", "Most recent date the stall rent was paid.", "DATE", "—", "NULL"),
        ],
    },
    {
        "name": "stalls_paymentrecord",
        "description": "Individual rent payment transactions linked to a stall.",
        "pk": "id",
        "fields": [
            ("id", "Unique identifier for each payment transaction.", "BIGINT", "20",
             "PRIMARY KEY, AUTO_INCREMENT, NOT NULL"),
            ("stall_id", "Reference to the stall that received the payment.", "BIGINT", "20",
             "FOREIGN KEY (stalls_stall.id), NOT NULL, ON DELETE CASCADE"),
            ("amount_paid", "Amount of money paid for the stall rent.", "DECIMAL", "10,2",
             "NOT NULL"),
            ("date_paid", "Calendar date when the payment was made.", "DATE", "—", "NOT NULL"),
            ("status", "Current verification status of the payment.", "VARCHAR", "20",
             "NOT NULL, DEFAULT 'Paid'"),
            ("payment_type", "Payment channel used (Cash, GCash, PayMaya, Bank Transfer).",
             "VARCHAR", "50", "NOT NULL, DEFAULT 'Cash'"),
            ("reference_number", "Optional transaction reference from the payment channel.",
             "VARCHAR", "100", "NULL"),
        ],
    },
    {
        "name": "stalls_systemsetting",
        "description": "Global configuration values for the market management system.",
        "pk": "id",
        "fields": [
            ("id", "Unique identifier for the settings record.", "BIGINT", "20",
             "PRIMARY KEY, AUTO_INCREMENT, NOT NULL"),
            ("market_name", "Official name of the public market.", "VARCHAR", "255",
             "NOT NULL, DEFAULT 'Salong Public Market'"),
            ("default_currency", "Three-letter currency code used by the system.", "VARCHAR", "10",
             "NOT NULL, DEFAULT 'PHP'"),
            ("market_address", "Complete address of the market office.", "VARCHAR", "255",
             "NOT NULL, DEFAULT ''"),
            ("email_notifications", "Flag that enables or disables email notifications.",
             "TINYINT", "1", "NOT NULL, DEFAULT 1"),
            ("payment_reminders", "Flag that enables or disables payment reminders.",
             "TINYINT", "1", "NOT NULL, DEFAULT 1"),
        ],
    },
    {
        "name": "stalls_userprofile",
        "description": "Role profile that extends each Django authentication user.",
        "pk": "id",
        "fields": [
            ("id", "Unique identifier for the user profile.", "BIGINT", "20",
             "PRIMARY KEY, AUTO_INCREMENT, NOT NULL"),
            ("user_id", "Reference to the Django authentication user account.", "BIGINT", "20",
             "FOREIGN KEY (auth_user.id), UNIQUE, NOT NULL, ON DELETE CASCADE"),
            ("role", "System role: superadmin, manager, or staff/collector.", "VARCHAR", "20",
             "NOT NULL, DEFAULT 'staff'"),
        ],
    },
    {
        "name": "stalls_activitylog",
        "description": "Audit trail of important actions performed inside the system.",
        "pk": "id",
        "fields": [
            ("id", "Unique identifier for the activity log entry.", "BIGINT", "20",
             "PRIMARY KEY, AUTO_INCREMENT, NOT NULL"),
            ("user_id", "Reference to the user who performed the action (NULL for system events).",
             "BIGINT", "20", "FOREIGN KEY (auth_user.id), NULL, ON DELETE SET NULL"),
            ("action", "Action category: user, stall, vendor, payment, settings, or auth.",
             "VARCHAR", "20", "NOT NULL, DEFAULT 'user'"),
            ("description", "Human-readable description of the activity.", "VARCHAR", "255",
             "NOT NULL"),
            ("timestamp", "Date and time when the activity occurred.", "DATETIME", "6",
             "NOT NULL, DEFAULT CURRENT_TIMESTAMP(6)"),
        ],
    },
    {
        "name": "auth_user",
        "description": "Django built-in user table used for authentication and role ownership.",
        "pk": "id",
        "fields": [
            ("id", "Unique identifier for the user account.", "INT", "11",
             "PRIMARY KEY, AUTO_INCREMENT, NOT NULL"),
            ("password", "Hashed password stored by Django's authentication framework.",
             "VARCHAR", "128", "NOT NULL"),
            ("last_login", "Date and time of the user's most recent login.", "DATETIME", "6", "NULL"),
            ("is_superuser", "Flag that grants all permissions to the user.", "TINYINT", "1",
             "NOT NULL"),
            ("username", "Unique login name of the user.", "VARCHAR", "150",
             "UNIQUE, NOT NULL"),
            ("first_name", "Given name of the user.", "VARCHAR", "150", "NOT NULL"),
            ("last_name", "Family name of the user.", "VARCHAR", "150", "NOT NULL"),
            ("email", "Email address of the user.", "VARCHAR", "254", "NOT NULL"),
            ("is_staff", "Flag that allows access to the Django admin site.", "TINYINT", "1",
             "NOT NULL"),
            ("is_active", "Flag that indicates whether the account can log in.", "TINYINT", "1",
             "NOT NULL"),
            ("date_joined", "Date and time when the account was created.", "DATETIME", "6",
             "NOT NULL"),
        ],
    },
]

ENTITY_ROWS = [
    ("stalls_vendor", "id", "None", "1 : M (Vendor to Stall)",
     "Stores the vendor master record. One vendor may be assigned to one or more stalls."),
    ("stalls_stall", "id", "vendor_id -> stalls_vendor.id", "M : 1 (Stall to Vendor); 1 : M (Stall to PaymentRecord)",
     "Stores physical stall information, rent rate, and payment due dates."),
    ("stalls_paymentrecord", "id", "stall_id -> stalls_stall.id", "M : 1 (PaymentRecord to Stall)",
     "Stores every rent payment transaction and its verification details."),
    ("stalls_systemsetting", "id", "None", "Standalone",
     "Stores global market name, currency, address, and notification settings."),
    ("stalls_userprofile", "id", "user_id -> auth_user.id", "1 : 1 (UserProfile to auth_user)",
     "Stores the system role assigned to each authenticated user."),
    ("stalls_activitylog", "id", "user_id -> auth_user.id", "M : 1 (ActivityLog to auth_user)",
     "Stores an audit trail of user and system actions."),
    ("auth_user", "id", "None", "1 : 1 (auth_user to UserProfile); 1 : M (auth_user to ActivityLog)",
     "Django authentication table used by login, permissions, and audit records."),
]

RELATIONSHIP_ROWS = [
    ("stalls_vendor -> stalls_stall", "1 : M",
     "One vendor can own or be assigned to many stalls, but each stall references only one vendor."),
    ("stalls_stall -> stalls_paymentrecord", "1 : M",
     "One stall can have many payment records, while each payment belongs to exactly one stall."),
    ("auth_user -> stalls_userprofile", "1 : 1",
     "Each authenticated user has exactly one role profile, and each profile belongs to one user."),
    ("auth_user -> stalls_activitylog", "1 : M",
     "One user can generate many activity log entries, while each log entry may reference one user."),
]

MERMAID_CONCEPTUAL = """erDiagram
    VENDOR ||--o{ STALL : "is assigned to"
    STALL ||--o{ PAYMENTRECORD : "generates"
    AUTH_USER ||--o| USERPROFILE : "owns"
    AUTH_USER ||--o{ ACTIVITYLOG : "performs"
    SYSTEMSETTING {
        bigint id PK
    }"""

MERMAID_LOGICAL = """erDiagram
    VENDOR ||--o{ STALL : "assigned_to"
    STALL ||--o{ PAYMENTRECORD : "has"
    AUTH_USER ||--o| USERPROFILE : "has_profile"
    AUTH_USER ||--o{ ACTIVITYLOG : "creates"
    VENDOR {
        bigint id PK
        varchar name
        varchar contact_number
        varchar category
    }
    STALL {
        bigint id PK
        varchar stall_number UK
        bigint vendor_id FK
        varchar vendor_name
        varchar category
        decimal rent_rate
        varchar contact_number
        date next_due_date
        date date_paid
    }
    PAYMENTRECORD {
        bigint id PK
        bigint stall_id FK
        decimal amount_paid
        date date_paid
        varchar status
        varchar payment_type
        varchar reference_number
    }
    USERPROFILE {
        bigint id PK
        bigint user_id FK
        varchar role
    }
    ACTIVITYLOG {
        bigint id PK
        bigint user_id FK
        varchar action
        varchar description
        datetime timestamp
    }
    SYSTEMSETTING {
        bigint id PK
        varchar market_name
        varchar default_currency
        varchar market_address
        tinyint email_notifications
        tinyint payment_reminders
    }"""

MERMAID_PHYSICAL = """erDiagram
    stalls_vendor ||--o{ stalls_stall : "vendor_id"
    stalls_stall ||--o{ stalls_paymentrecord : "stall_id"
    auth_user ||--o| stalls_userprofile : "user_id"
    auth_user ||--o{ stalls_activitylog : "user_id"
    stalls_vendor {
        BIGINT id PK "AUTO_INCREMENT"
        VARCHAR name "VARCHAR(100) NOT NULL"
        VARCHAR contact_number "VARCHAR(20) NOT NULL"
        VARCHAR category "VARCHAR(50) NULL"
    }
    stalls_stall {
        BIGINT id PK "AUTO_INCREMENT"
        VARCHAR stall_number "VARCHAR(50) UNIQUE NOT NULL"
        BIGINT vendor_id FK "NULL, ON DELETE SET NULL"
        VARCHAR vendor_name "VARCHAR(100) NULL"
        VARCHAR category "VARCHAR(100) NULL"
        DECIMAL rent_rate "DECIMAL(10,2) DEFAULT 0.00"
        VARCHAR contact_number "VARCHAR(20) NULL"
        DATE next_due_date "NULL"
        DATE date_paid "NULL"
    }
    stalls_paymentrecord {
        BIGINT id PK "AUTO_INCREMENT"
        BIGINT stall_id FK "NOT NULL, ON DELETE CASCADE"
        DECIMAL amount_paid "DECIMAL(10,2) NOT NULL"
        DATE date_paid "NOT NULL"
        VARCHAR status "VARCHAR(20) DEFAULT 'Paid'"
        VARCHAR payment_type "VARCHAR(50) DEFAULT 'Cash'"
        VARCHAR reference_number "VARCHAR(100) NULL"
    }
    stalls_systemsetting {
        BIGINT id PK "AUTO_INCREMENT"
        VARCHAR market_name "VARCHAR(255) DEFAULT 'Salong Public Market'"
        VARCHAR default_currency "VARCHAR(10) DEFAULT 'PHP'"
        VARCHAR market_address "VARCHAR(255) DEFAULT ''"
        TINYINT email_notifications "TINYINT(1) DEFAULT 1"
        TINYINT payment_reminders "TINYINT(1) DEFAULT 1"
    }
    stalls_userprofile {
        BIGINT id PK "AUTO_INCREMENT"
        BIGINT user_id FK "UNIQUE NOT NULL"
        VARCHAR role "VARCHAR(20) DEFAULT 'staff'"
    }
    stalls_activitylog {
        BIGINT id PK "AUTO_INCREMENT"
        BIGINT user_id FK "NULL, ON DELETE SET NULL"
        VARCHAR action "VARCHAR(20) DEFAULT 'user'"
        VARCHAR description "VARCHAR(255) NOT NULL"
        DATETIME timestamp "NOT NULL"
    }"""


# ---------------------------------------------------------------------------
# SQL statement data
# ---------------------------------------------------------------------------
SELECT_QUERIES = [
    {
        "title": "Concatenate Vendor Name and Contact Number",
        "problem": "The market administrator needs a single readable column that combines each vendor's name and contact number for the vendor directory.",
        "sql": """SELECT CONCAT(name, ' - ', contact_number) AS vendor_contact
FROM stalls_vendor
ORDER BY name ASC;""",
    },
    {
        "title": "Filter Stalls by Rent Range Using BETWEEN",
        "problem": "The collections team wants to list all stalls whose monthly rent falls between 1,000.00 and 3,000.00 pesos.",
        "sql": """SELECT stall_number, vendor_name, rent_rate
FROM stalls_stall
WHERE rent_rate BETWEEN 1000.00 AND 3000.00
ORDER BY rent_rate ASC;""",
    },
    {
        "title": "Search Vendors by Partial Name Using LIKE",
        "problem": "The staff needs to search for vendors whose registered name contains the word Market.",
        "sql": """SELECT id, name, contact_number
FROM stalls_vendor
WHERE name LIKE '%Market%'
ORDER BY name ASC;""",
    },
    {
        "title": "Exclude Food-Related Stalls Using NOT LIKE",
        "problem": "The market head wants a list of non-food stalls for the dry goods and services section report.",
        "sql": """SELECT stall_number, vendor_name, category
FROM stalls_stall
WHERE category NOT LIKE '%Food%'
ORDER BY stall_number ASC;""",
    },
    {
        "title": "Sort Stalls by Highest Rent Rate",
        "problem": "Management needs a ranking of stalls from the highest to the lowest rent rate for revenue planning.",
        "sql": """SELECT stall_number, vendor_name, rent_rate
FROM stalls_stall
ORDER BY rent_rate DESC;""",
    },
    {
        "title": "Count Stalls per Category Using GROUP BY",
        "problem": "The market administrator needs to know how many stalls belong to each category.",
        "sql": """SELECT category, COUNT(*) AS total_stalls
FROM stalls_stall
GROUP BY category
ORDER BY total_stalls DESC;""",
    },
    {
        "title": "Compute Total Payments Collected",
        "problem": "The treasurer needs the total amount of rent collected from all payment records.",
        "sql": """SELECT SUM(amount_paid) AS total_collected
FROM stalls_paymentrecord;""",
    },
    {
        "title": "Classify Stall Payment Status Using CASE WHEN",
        "problem": "The system must label every stall as Paid, Overdue, or Pending based on its payment dates.",
        "sql": """SELECT stall_number,
       vendor_name,
       CASE
           WHEN date_paid IS NOT NULL THEN 'Paid'
           WHEN next_due_date < CURDATE() THEN 'Overdue'
           ELSE 'Pending'
       END AS payment_status
FROM stalls_stall
ORDER BY stall_number ASC;""",
    },
    {
        "title": "List Payments Recorded Today",
        "problem": "The collector needs to see all payments recorded on the current date for daily remittance.",
        "sql": """SELECT id, stall_id, amount_paid, payment_type, date_paid
FROM stalls_paymentrecord
WHERE date_paid = CURDATE();""",
    },
    {
        "title": "Summarize Monthly Collections Using YEAR and MONTH",
        "problem": "Management needs a monthly summary of rent collections for the annual financial report.",
        "sql": """SELECT YEAR(date_paid) AS payment_year,
       MONTH(date_paid) AS payment_month,
       SUM(amount_paid) AS monthly_total
FROM stalls_paymentrecord
GROUP BY YEAR(date_paid), MONTH(date_paid)
ORDER BY payment_year DESC, payment_month DESC;""",
    },
    {
        "title": "Count Distinct Payment Types",
        "problem": "The cashier needs to know how many different payment channels were actually used by vendors.",
        "sql": """SELECT COUNT(DISTINCT payment_type) AS distinct_payment_types
FROM stalls_paymentrecord;""",
    },
    {
        "title": "Calculate Average Stall Rent",
        "problem": "The market manager needs the average monthly rent to evaluate the fairness of current rates.",
        "sql": """SELECT ROUND(AVG(rent_rate), 2) AS average_rent
FROM stalls_stall;""",
    },
    {
        "title": "Find Highest and Lowest Rent Rates",
        "problem": "Management needs the highest and lowest rent values to establish the market's rent range.",
        "sql": """SELECT MAX(rent_rate) AS highest_rent,
       MIN(rent_rate) AS lowest_rent
FROM stalls_stall;""",
    },
    {
        "title": "Display Vendor Names in Uppercase",
        "problem": "The report generator needs vendor names in uppercase and categories in lowercase for a standardized printout.",
        "sql": """SELECT UPPER(name) AS vendor_name_upper,
       LOWER(category) AS category_lower
FROM stalls_vendor
ORDER BY name ASC;""",
    },
    {
        "title": "Measure Length of Vendor Names",
        "problem": "The system analyst needs to identify the longest vendor names to adjust the printed receipt layout.",
        "sql": """SELECT name, LENGTH(name) AS name_length
FROM stalls_vendor
ORDER BY name_length DESC;""",
    },
    {
        "title": "Round Payment Amounts to Whole Pesos",
        "problem": "The receipt module needs payment amounts rounded to the nearest whole peso for display.",
        "sql": """SELECT id, amount_paid, ROUND(amount_paid, 0) AS rounded_amount
FROM stalls_paymentrecord
ORDER BY id ASC;""",
    },
    {
        "title": "Compute Days Until Next Due Date Using DATEDIFF",
        "problem": "The collector needs to know how many days remain before each stall's next rent due date.",
        "sql": """SELECT stall_number,
       next_due_date,
       DATEDIFF(next_due_date, CURDATE()) AS days_remaining
FROM stalls_stall
WHERE next_due_date IS NOT NULL
ORDER BY days_remaining ASC;""",
    },
    {
        "title": "Format Payment Dates Using DATE_FORMAT",
        "problem": "The official receipt needs payment dates displayed in a readable Month Day, Year format.",
        "sql": """SELECT id,
       DATE_FORMAT(date_paid, '%M %d, %Y') AS formatted_date,
       amount_paid
FROM stalls_paymentrecord
ORDER BY date_paid DESC;""",
    },
    {
        "title": "Replace Missing Reference Numbers Using IFNULL",
        "problem": "The payment report must show a readable label instead of a blank value when no reference number exists.",
        "sql": """SELECT id,
       payment_type,
       IFNULL(reference_number, 'No Reference') AS reference_display
FROM stalls_paymentrecord
ORDER BY id ASC;""",
    },
    {
        "title": "Group Payments by Type and Filter Using HAVING",
        "problem": "The treasurer needs payment totals per channel, but only for channels that have collected a positive amount.",
        "sql": """SELECT payment_type,
       COUNT(*) AS payment_count,
       SUM(amount_paid) AS total_amount
FROM stalls_paymentrecord
GROUP BY payment_type
HAVING SUM(amount_paid) > 0
ORDER BY total_amount DESC;""",
    },
    {
        "title": "List Stalls with Rent Above a Threshold",
        "problem": "Management wants to identify high-value stalls that pay more than 2,000.00 pesos in monthly rent.",
        "sql": """SELECT stall_number, vendor_name, rent_rate
FROM stalls_stall
WHERE rent_rate > 2000.00
ORDER BY rent_rate DESC;""",
    },
    {
        "title": "Sort Stalls by Category then Stall Number",
        "problem": "The market map report needs stalls arranged alphabetically by category and then by stall number.",
        "sql": """SELECT category, stall_number, vendor_name
FROM stalls_stall
ORDER BY category ASC, stall_number ASC;""",
    },
    {
        "title": "Retrieve the Five Most Expensive Stalls Using LIMIT",
        "problem": "Management needs a short list of the five highest-rent stalls for the premium section review.",
        "sql": """SELECT stall_number, vendor_name, rent_rate
FROM stalls_stall
ORDER BY rent_rate DESC
LIMIT 5;""",
    },
    {
        "title": "Count Active Vendors with Contact Numbers",
        "problem": "The administrator needs to verify how many vendor records have a usable contact number.",
        "sql": """SELECT COUNT(*) AS vendors_with_contact
FROM stalls_vendor
WHERE contact_number IS NOT NULL
  AND contact_number <> '';""",
    },
    {
        "title": "List Distinct Stall Categories",
        "problem": "The report designer needs the complete list of unique stall categories used in the market.",
        "sql": """SELECT DISTINCT category
FROM stalls_stall
WHERE category IS NOT NULL
ORDER BY category ASC;""",
    },
    {
        "title": "Show Day Name of Each Payment Date",
        "problem": "The collections supervisor wants to know which day of the week each payment was recorded.",
        "sql": """SELECT id,
       date_paid,
       DAYNAME(date_paid) AS day_name
FROM stalls_paymentrecord
ORDER BY date_paid DESC;""",
    },
    {
        "title": "Concatenate Market Information Using CONCAT_WS",
        "problem": "The system needs a single formatted line containing the market name, address, and currency for the header.",
        "sql": """SELECT CONCAT_WS(' | ', market_name, market_address, default_currency) AS market_information
FROM stalls_systemsetting;""",
    },
    {
        "title": "Classify Payment Amounts Using CASE WHEN",
        "problem": "The financial report must classify payments as High Value, Medium Value, or Low Value.",
        "sql": """SELECT id,
       amount_paid,
       CASE
           WHEN amount_paid >= 5000 THEN 'High Value'
           WHEN amount_paid >= 1000 THEN 'Medium Value'
           ELSE 'Low Value'
       END AS amount_category
FROM stalls_paymentrecord
ORDER BY amount_paid DESC;""",
    },
    {
        "title": "Filter Payments Within a Date Range",
        "problem": "The accountant needs all payments recorded within the calendar year 2026.",
        "sql": """SELECT id, stall_id, amount_paid, date_paid
FROM stalls_paymentrecord
WHERE date_paid BETWEEN '2026-01-01' AND '2026-12-31'
ORDER BY date_paid ASC;""",
    },
    {
        "title": "Count Overdue Stalls Using a Date Filter",
        "problem": "Management needs the total number of stalls that are past their due date and still unpaid.",
        "sql": """SELECT COUNT(*) AS overdue_stalls
FROM stalls_stall
WHERE next_due_date < CURDATE()
  AND date_paid IS NULL;""",
    },
]

INSERT_QUERIES = [
    {
        "title": "Insert a Single Vendor",
        "problem": "A new vegetable vendor has registered and must be added to the vendor master list.",
        "sql": """INSERT INTO stalls_vendor (name, contact_number, category)
VALUES ('Maria Santos', '09171234567', 'Vegetables');""",
    },
    {
        "title": "Insert a Single Stall with Vendor Foreign Key",
        "problem": "A newly constructed stall must be registered and assigned to an existing vendor.",
        "sql": """INSERT INTO stalls_stall
    (stall_number, vendor_id, vendor_name, category, rent_rate, contact_number, next_due_date, date_paid)
VALUES
    ('S-101', 1, 'Maria Santos', 'Vegetables', 1500.00, '09171234567', '2026-12-01', NULL);""",
    },
    {
        "title": "Insert a Payment with a NULL Reference Number",
        "problem": "A cash payment has no external reference number, so the reference field must be stored as NULL.",
        "sql": """INSERT INTO stalls_paymentrecord
    (stall_id, amount_paid, date_paid, status, payment_type, reference_number)
VALUES
    (1, 1500.00, CURDATE(), 'Paid', 'Cash', NULL);""",
    },
    {
        "title": "Insert a Vendor Only If It Does Not Exist",
        "problem": "The registration form must avoid duplicate vendor records when the same vendor submits twice.",
        "sql": """INSERT INTO stalls_vendor (name, contact_number, category)
SELECT 'Maria Santos', '09171234567', 'Vegetables'
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM stalls_vendor WHERE name = 'Maria Santos'
);""",
    },
    {
        "title": "Insert Multiple Vendors in One Statement",
        "problem": "The market office encoded three new vendors during the same registration session.",
        "sql": """INSERT INTO stalls_vendor (name, contact_number, category)
VALUES
    ('Juan Dela Cruz', '09181234567', 'Meat'),
    ('Ana Reyes', '09191234567', 'Fish'),
    ('Pedro Lim', '09201234567', 'Dry Goods');""",
    },
    {
        "title": "Insert Multiple Payment Records",
        "problem": "The cashier needs to post several rent payments collected on different dates in one batch.",
        "sql": """INSERT INTO stalls_paymentrecord
    (stall_id, amount_paid, date_paid, status, payment_type, reference_number)
VALUES
    (1, 1500.00, '2026-11-01', 'Paid', 'GCash', 'GC-1001'),
    (2, 1800.00, '2026-11-02', 'Paid', 'Cash', NULL),
    (3, 2000.00, '2026-11-03', 'Paid', 'Bank Transfer', 'BT-2001');""",
    },
    {
        "title": "Insert Default System Settings",
        "problem": "A fresh installation needs its initial market name, currency, address, and notification flags.",
        "sql": """INSERT INTO stalls_systemsetting
    (market_name, default_currency, market_address, email_notifications, payment_reminders)
VALUES
    ('Salong Public Market', 'PHP', 'Salong, Valencia, Bohol', 1, 1);""",
    },
    {
        "title": "Create a User Profile Only If Missing",
        "problem": "An existing Django user needs a manager role profile, but the profile must not be duplicated.",
        "sql": """INSERT INTO stalls_userprofile (user_id, role)
SELECT id, 'manager'
FROM auth_user
WHERE username = 'laravel'
  AND NOT EXISTS (
      SELECT 1 FROM stalls_userprofile WHERE user_id = auth_user.id
  );""",
    },
    {
        "title": "Insert an Activity Log with a NULL User",
        "problem": "A system initialization event has no logged-in user, so the audit record must use a NULL user reference.",
        "sql": """INSERT INTO stalls_activitylog (user_id, action, description, timestamp)
VALUES (NULL, 'settings', 'System initialized with default configuration', NOW(6));""",
    },
    {
        "title": "Insert a Stall with NULL Optional Fields",
        "problem": "A vacant stall must be registered before a vendor is assigned, so optional fields remain NULL.",
        "sql": """INSERT INTO stalls_stall
    (stall_number, vendor_id, vendor_name, category, rent_rate, contact_number, next_due_date, date_paid)
VALUES
    ('S-102', NULL, NULL, NULL, 0.00, NULL, NULL, NULL);""",
    },
]

UPDATE_QUERIES = [
    {
        "title": "Update a Vendor's Contact Number",
        "problem": "Maria Santos reported a new mobile number that must replace her old contact detail.",
        "sql": """UPDATE stalls_vendor
SET contact_number = '09991234567'
WHERE name = 'Maria Santos';""",
    },
    {
        "title": "Update Rent Rate by Stall Number",
        "problem": "The market council approved a rent adjustment for stall S-101.",
        "sql": """UPDATE stalls_stall
SET rent_rate = 1750.00
WHERE stall_number = 'S-101';""",
    },
    {
        "title": "Bulk Update Categories Using CASE WHEN",
        "problem": "Management wants to reclassify all stalls into Premium, Standard, and Economy tiers based on rent.",
        "sql": """UPDATE stalls_stall
SET category = CASE
    WHEN rent_rate >= 3000 THEN 'Premium'
    WHEN rent_rate >= 1500 THEN 'Standard'
    ELSE 'Economy'
END;""",
    },
    {
        "title": "Update Multiple Stalls Using IN",
        "problem": "The next rent cycle due date must be applied to a specific group of stalls.",
        "sql": """UPDATE stalls_stall
SET next_due_date = '2026-12-31'
WHERE stall_number IN ('S-101', 'S-102', 'S-103');""",
    },
    {
        "title": "Update Multiple Columns in One Statement",
        "problem": "A stall transfer requires the vendor name, contact number, and category to be corrected together.",
        "sql": """UPDATE stalls_stall
SET vendor_name = 'Maria Santos',
    contact_number = '09171234567',
    category = 'Vegetables'
WHERE stall_number = 'S-101';""",
    },
    {
        "title": "Mark Payments as Verified on a Specific Date",
        "problem": "All payments recorded on November 1, 2026 have been reconciled with the bank deposit.",
        "sql": """UPDATE stalls_paymentrecord
SET status = 'Verified'
WHERE date_paid = '2026-11-01';""",
    },
    {
        "title": "Update Payment Status Based on Payment Type",
        "problem": "Cash payments must be marked Cleared while digital payments await verification.",
        "sql": """UPDATE stalls_paymentrecord
SET status = CASE
    WHEN payment_type = 'Cash' THEN 'Cleared'
    ELSE 'Pending Verification'
END
WHERE amount_paid > 0;""",
    },
    {
        "title": "Set Date Paid for Stalls with a Due Date",
        "problem": "The collector needs to record today's date for all stalls that have an active due date and no payment yet.",
        "sql": """UPDATE stalls_stall
SET date_paid = CURDATE()
WHERE next_due_date IS NOT NULL
  AND date_paid IS NULL;""",
    },
    {
        "title": "Update System Settings",
        "problem": "The market office changed its official name and wants payment reminders enabled again.",
        "sql": """UPDATE stalls_systemsetting
SET market_name = 'Salong Public Market',
    default_currency = 'PHP',
    payment_reminders = 1
WHERE id = 1;""",
    },
    {
        "title": "Update a User Role by Username",
        "problem": "The account named laravel has been promoted from staff to market manager.",
        "sql": """UPDATE stalls_userprofile
SET role = 'manager'
WHERE user_id = (
    SELECT id FROM auth_user WHERE username = 'laravel' LIMIT 1
);""",
    },
]

DELETE_QUERIES = [
    {
        "title": "Delete a Payment Record by ID",
        "problem": "A duplicate payment entry with ID 1 must be removed after reconciliation.",
        "sql": """DELETE FROM stalls_paymentrecord
WHERE id = 1;""",
    },
    {
        "title": "Delete a Vendor by Name",
        "problem": "A vendor who permanently left the market must be removed from the vendor master list.",
        "sql": """DELETE FROM stalls_vendor
WHERE name = 'Pedro Lim';""",
    },
    {
        "title": "Delete Payments Recorded on a Specific Date",
        "problem": "All payment entries created on November 1, 2026 were entered in error and must be deleted.",
        "sql": """DELETE FROM stalls_paymentrecord
WHERE DATE(date_paid) = '2026-11-01';""",
    },
    {
        "title": "Delete Stalls Using a Subquery with IN",
        "problem": "Stalls assigned to vendors in the Fish category are being retired and must be removed.",
        "sql": """DELETE FROM stalls_stall
WHERE vendor_id IN (
    SELECT id FROM stalls_vendor WHERE category = 'Fish'
);""",
    },
    {
        "title": "Delete Records with Zero-Value Conditions",
        "problem": "Vacant or incomplete stall records with zero rent and no vendor details must be cleaned up.",
        "sql": """DELETE FROM stalls_stall
WHERE rent_rate = 0.00
   OR (vendor_name IS NULL AND contact_number IS NULL);""",
    },
]

SUBQUERY_QUERIES = [
    {
        "title": "Find a Stall Using a Scalar Subquery with LIMIT 1",
        "problem": "Management wants to identify the stall that currently pays the highest rent.",
        "sql": """SELECT stall_number, vendor_name, rent_rate
FROM stalls_stall
WHERE rent_rate = (
    SELECT rent_rate
    FROM stalls_stall
    ORDER BY rent_rate DESC
    LIMIT 1
);""",
    },
    {
        "title": "Find Vendors Using IN with a Subquery",
        "problem": "The report needs the vendors who own stalls with a rent rate greater than 2,000.00 pesos.",
        "sql": """SELECT id, name, contact_number
FROM stalls_vendor
WHERE id IN (
    SELECT vendor_id
    FROM stalls_stall
    WHERE rent_rate > 2000.00
);""",
    },
    {
        "title": "Show Total Payments per Stall Using a Scalar Subquery",
        "problem": "The dashboard needs each stall's lifetime payment total displayed beside the stall record.",
        "sql": """SELECT s.stall_number,
       s.vendor_name,
       (
           SELECT SUM(p.amount_paid)
           FROM stalls_paymentrecord p
           WHERE p.stall_id = s.id
       ) AS total_paid
FROM stalls_stall s
ORDER BY total_paid DESC;""",
    },
    {
        "title": "Find Stalls Without Payments Using NOT IN",
        "problem": "The collector needs a list of stalls that have never submitted a rent payment.",
        "sql": """SELECT stall_number, vendor_name
FROM stalls_stall
WHERE id NOT IN (
    SELECT stall_id
    FROM stalls_paymentrecord
);""",
    },
    {
        "title": "Find Stalls Paying Above Average Rent",
        "problem": "Management wants to compare high-paying stalls against the market-wide average rent.",
        "sql": """SELECT stall_number, vendor_name, rent_rate
FROM stalls_stall
WHERE rent_rate > (
    SELECT AVG(rent_rate)
    FROM stalls_stall
)
ORDER BY rent_rate DESC;""",
    },
]

JOIN_QUERIES = [
    {
        "title": "INNER JOIN Vendors and Stalls with CONCAT",
        "problem": "The vendor directory needs each vendor's formatted contact information together with the assigned stall.",
        "sql": """SELECT CONCAT(v.name, ' (', v.contact_number, ')') AS vendor_contact,
       s.stall_number,
       s.rent_rate
FROM stalls_vendor v
INNER JOIN stalls_stall s ON v.id = s.vendor_id
ORDER BY v.name ASC;""",
    },
    {
        "title": "LEFT JOIN Vendors and Stalls to Show Unassigned Vendors",
        "problem": "Management wants a complete vendor list that also shows vendors who have not yet been assigned a stall.",
        "sql": """SELECT v.name,
       IFNULL(s.stall_number, 'No Stall') AS stall_number
FROM stalls_vendor v
LEFT JOIN stalls_stall s ON v.id = s.vendor_id
ORDER BY v.name ASC;""",
    },
    {
        "title": "INNER JOIN Stalls and Payment Records",
        "problem": "The cashier needs a combined view of every stall and its corresponding payment transactions.",
        "sql": """SELECT s.stall_number,
       p.amount_paid,
       p.payment_type,
       p.date_paid
FROM stalls_stall s
INNER JOIN stalls_paymentrecord p ON s.id = p.stall_id
ORDER BY p.date_paid DESC;""",
    },
    {
        "title": "INNER JOIN Stalls, Vendors, and Payments with CONCAT",
        "problem": "The financial report needs a single line that combines the vendor, stall, and payment details.",
        "sql": """SELECT CONCAT(v.name, ' - Stall ', s.stall_number) AS vendor_stall,
       p.amount_paid,
       p.payment_type
FROM stalls_vendor v
INNER JOIN stalls_stall s ON v.id = s.vendor_id
INNER JOIN stalls_paymentrecord p ON s.id = p.stall_id
ORDER BY v.name ASC, p.date_paid DESC;""",
    },
    {
        "title": "LEFT JOIN Stalls to Payments to Detect Unpaid Stalls",
        "problem": "The collector needs the total payment per stall, including stalls that have never paid.",
        "sql": """SELECT s.stall_number,
       s.vendor_name,
       IFNULL(SUM(p.amount_paid), 0) AS total_paid
FROM stalls_stall s
LEFT JOIN stalls_paymentrecord p ON s.id = p.stall_id
GROUP BY s.id, s.stall_number, s.vendor_name
ORDER BY total_paid ASC;""",
    },
    {
        "title": "INNER JOIN User Profiles and Auth Users with CONCAT",
        "problem": "The administrator needs a user directory showing each account's full name, username, email, and role.",
        "sql": """SELECT CONCAT(u.first_name, ' ', u.last_name) AS full_name,
       u.username,
       u.email,
       up.role
FROM auth_user u
INNER JOIN stalls_userprofile up ON u.id = up.user_id
ORDER BY full_name ASC;""",
    },
    {
        "title": "LEFT JOIN Activity Logs and Users",
        "problem": "The audit report must show who performed each activity, including system events with no user.",
        "sql": """SELECT IFNULL(CONCAT(u.first_name, ' ', u.last_name), 'System') AS actor,
       a.action,
       a.description,
       a.timestamp
FROM stalls_activitylog a
LEFT JOIN auth_user u ON a.user_id = u.id
ORDER BY a.timestamp DESC;""",
    },
    {
        "title": "INNER JOIN with GROUP BY to Total Collections per Stall",
        "problem": "Management needs the number of payments and total collection for every stall that has paid.",
        "sql": """SELECT CONCAT(s.stall_number, ' - ', IFNULL(s.vendor_name, 'Unassigned')) AS stall_label,
       COUNT(p.id) AS payment_count,
       SUM(p.amount_paid) AS total_collected
FROM stalls_stall s
INNER JOIN stalls_paymentrecord p ON s.id = p.stall_id
GROUP BY s.id, s.stall_number, s.vendor_name
ORDER BY total_collected DESC;""",
    },
    {
        "title": "LEFT JOIN Stalls and Payments to Find Stalls Without Payments",
        "problem": "The system must flag stalls that have no payment record at all for follow-up.",
        "sql": """SELECT s.stall_number, s.vendor_name
FROM stalls_stall s
LEFT JOIN stalls_paymentrecord p ON s.id = p.stall_id
WHERE p.id IS NULL
ORDER BY s.stall_number ASC;""",
    },
    {
        "title": "Multi-Table JOIN with CONCAT_WS for Payment Audit Report",
        "problem": "The auditor needs a complete payment audit line combining vendor, stall, payment type, and date.",
        "sql": """SELECT CONCAT_WS(' | ',
           v.name,
           s.stall_number,
           p.payment_type,
           DATE_FORMAT(p.date_paid, '%Y-%m-%d')
       ) AS audit_line,
       p.amount_paid,
       p.status
FROM stalls_vendor v
INNER JOIN stalls_stall s ON v.id = s.vendor_id
INNER JOIN stalls_paymentrecord p ON s.id = p.stall_id
ORDER BY p.date_paid DESC;""",
    },
]


# ---------------------------------------------------------------------------
# Document builders
# ---------------------------------------------------------------------------
def setup_document():
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.different_first_page_header_footer = True

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.element.get_or_add_rPr()
    rfonts = normal.element.rPr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        normal.element.rPr.append(rfonts)
    rfonts.set(qn("w:ascii"), "Times New Roman")
    rfonts.set(qn("w:hAnsi"), "Times New Roman")
    rfonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.5

    for name, size in (("Heading 1", 16), ("Heading 2", 14), ("Heading 3", 12)):
        style = doc.styles[name]
        style.font.name = "Times New Roman"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = NAVY
        style.paragraph_format.space_before = Pt(14)
        style.paragraph_format.space_after = Pt(8)
        style.paragraph_format.keep_with_next = True
        style.element.get_or_add_rPr()
        rfonts = style.element.rPr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = OxmlElement("w:rFonts")
            style.element.rPr.append(rfonts)
        rfonts.set(qn("w:ascii"), "Times New Roman")
        rfonts.set(qn("w:hAnsi"), "Times New Roman")
        rfonts.set(qn("w:eastAsia"), "Times New Roman")

    header = section.header
    header_paragraph = header.paragraphs[0]
    header_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header_run = header_paragraph.add_run("Market Stall Management System  |  Database Design")
    set_run_font(header_run, size=9, italic=True, color=DARK_GRAY)

    footer = section.footer
    footer_paragraph = footer.paragraphs[0]
    footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    page_run = footer_paragraph.add_run("Page ")
    set_run_font(page_run, size=9)
    add_field(footer_paragraph, "PAGE")
    of_run = footer_paragraph.add_run(" of ")
    set_run_font(of_run, size=9)
    add_field(footer_paragraph, "NUMPAGES")

    core = doc.core_properties
    core.title = "Market Database Design"
    core.subject = "Market Stall Management System (market_db)"
    core.author = "BSIT Group"
    core.comments = "Database design document generated from the Django models."
    return doc


def build_title_page(doc):
    for _ in range(3):
        doc.add_paragraph()

    school = doc.add_paragraph()
    school.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = school.add_run("[SCHOOL NAME]")
    set_run_font(run, size=16, bold=True)

    college = doc.add_paragraph()
    college.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = college.add_run("College of Information Technology")
    set_run_font(run, size=13)

    for _ in range(2):
        doc.add_paragraph()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("MARKET STALL MANAGEMENT SYSTEM")
    set_run_font(run, size=24, bold=True, color=NAVY)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Database Design and Implementation")
    set_run_font(run, size=14, italic=True)

    db_name = doc.add_paragraph()
    db_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = db_name.add_run("Database Name: market_db")
    set_run_font(run, size=12)

    for _ in range(2):
        doc.add_paragraph()

    program = doc.add_paragraph()
    program.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = program.add_run("Bachelor of Science in Information Technology (BSIT)")
    set_run_font(run, size=14, bold=True)

    for _ in range(2):
        doc.add_paragraph()

    prepared = doc.add_paragraph()
    prepared.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = prepared.add_run("Prepared by:")
    set_run_font(run, size=12, bold=True)

    members = [
        "[Group Member 1] – [Role / Contribution]",
        "[Group Member 2] – [Role / Contribution]",
        "[Group Member 3] – [Role / Contribution]",
        "[Group Member 4] – [Role / Contribution]",
    ]
    for member in members:
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(2)
        run = paragraph.add_run(member)
        set_run_font(run, size=12)

    for _ in range(3):
        doc.add_paragraph()

    date_paragraph = doc.add_paragraph()
    date_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = date_paragraph.add_run(f"Date: {date.today().strftime('%B %d, %Y')}")
    set_run_font(run, size=12, bold=True)

    doc.add_page_break()


def build_system_description(doc):
    doc.add_heading("2. Proposed System Description", level=1)
    add_body(
        doc,
        "The Market Stall Management System is a web-based information system designed to replace the "
        "manual logbooks, spreadsheets, and paper receipts currently used in the public market. Its primary "
        "purpose is to centralize vendor registration, stall assignment, rent monitoring, and payment "
        "recording into a single database named market_db. Instead of searching through handwritten records, "
        "market staff can retrieve a vendor's profile, the stall assigned to that vendor, the monthly rent "
        "rate, the next due date, and the complete payment history within seconds. The system also provides "
        "role-based access for super administrators, market managers, and staff or collectors, ensuring that "
        "sensitive operations such as user management and settings changes are restricted to authorized "
        "personnel. By digitizing these workflows, the market office reduces duplicate entries, improves "
        "transparency, and produces accurate reports for daily collections and long-term planning.",
    )
    add_body(
        doc,
        "Vendor and stall tracking is the core operational feature of the system. Every vendor is stored in "
        "the stalls_vendor table with a unique identifier, complete name, contact number, and business "
        "category. Physical stalls are stored in the stalls_stall table with a unique stall number, an "
        "optional foreign key to the assigned vendor, the rent rate, the next due date, and the most recent "
        "date paid. Because a vendor may occupy more than one stall while each stall references only one "
        "vendor, the design models a one-to-many relationship that reflects the real layout of the market. "
        "Payment transactions are stored separately in stalls_paymentrecord, where each row captures the "
        "amount paid, the payment date, the channel used, the verification status, and an optional reference "
        "number. This separation allows the system to compute balances, flag overdue stalls, and generate "
        "collection summaries without altering the master stall record.",
    )
    add_body(
        doc,
        "The database provides significant benefits over manual record keeping. Referential integrity is "
        "enforced through foreign keys: deleting a vendor sets the related stall's vendor reference to NULL, "
        "while deleting a stall cascades to its payment records, preventing orphaned transactions. "
        "Normalization keeps vendor, stall, payment, user, and configuration data in focused tables, which "
        "reduces redundancy and makes updates safer. MySQL transactions and constraints protect the accuracy "
        "of financial records, while indexed primary keys and unique fields such as stall_number and username "
        "speed up searches and prevent duplicates. The activity log table adds an audit trail for "
        "accountability, and the system settings table allows the market name, currency, address, and "
        "notification preferences to be configured without code changes. Overall, market_db gives the market "
        "office a reliable, scalable, and report-ready foundation for daily operations.",
    )
    doc.add_page_break()


def build_design_sections(doc):
    doc.add_heading("3. Conceptual Design, Logical Design, and Physical Design", level=1)
    add_body(
        doc,
        "This section presents the three levels of database design used for market_db. Each level has its own "
        "full-page section, a figure caption, a bordered space for the draw.io diagram, and the corresponding "
        "Mermaid.js erDiagram reference text.",
    )
    doc.add_page_break()

    doc.add_heading("3.1 Conceptual Design", level=1)
    add_body(
        doc,
        "The conceptual design shows the high-level entities of the system and the business relationships "
        "between them without technical data types. It answers what the organization needs to track: vendors, "
        "stalls, payments, users, user roles, activity logs, and system settings.",
    )
    add_caption(doc, "Figure 3.1 Conceptual Design Diagram (paste the draw.io conceptual diagram here)")
    add_placeholder_box(
        doc,
        "[PASTE CONCEPTUAL DESIGN DIAGRAM HERE]",
        height=4.3,
        note="Recommended: export the draw.io conceptual diagram as PNG at 300 DPI.",
    )
    add_mermaid_reference(doc, "Mermaid.js erDiagram Reference – Conceptual Design", MERMAID_CONCEPTUAL)
    doc.add_page_break()

    doc.add_heading("3.2 Logical Design", level=1)
    add_body(
        doc,
        "The logical design translates the conceptual model into relational entities with primary keys, "
        "foreign keys, unique attributes, and cardinality. It shows how vendors connect to stalls and how "
        "stalls connect to payment records, while user profiles and activity logs connect to the "
        "authentication user table.",
    )
    add_caption(doc, "Figure 3.2 Logical Design Diagram (paste the draw.io logical diagram here)")
    add_placeholder_box(
        doc,
        "[PASTE LOGICAL DESIGN DIAGRAM HERE]",
        height=4.0,
        note="Show primary keys (PK), foreign keys (FK), and cardinality labels in this diagram.",
    )
    add_mermaid_reference(doc, "Mermaid.js erDiagram Reference – Logical Design", MERMAID_LOGICAL)
    doc.add_page_break()

    doc.add_heading("3.3 Physical Design", level=1)
    add_body(
        doc,
        "The physical design maps the logical model to actual MySQL tables, columns, data types, lengths, "
        "defaults, and constraints used by phpMyAdmin. It reflects the Django migrations for the stalls app "
        "and the built-in auth_user table required by Django authentication.",
    )
    add_caption(doc, "Figure 3.3 Physical Design Diagram (paste the draw.io physical diagram here)")
    add_placeholder_box(
        doc,
        "[PASTE PHYSICAL DESIGN DIAGRAM HERE]",
        height=3.8,
        note="Include MySQL data types, lengths, NULL rules, defaults, and index markers.",
    )
    add_mermaid_reference(doc, "Mermaid.js erDiagram Reference – Physical Design", MERMAID_PHYSICAL)
    doc.add_page_break()


def build_list_of_tables(doc):
    doc.add_heading("4. List of Tables", level=1)
    add_body(
        doc,
        "The market_db database is composed of the following main tables. The Django framework also creates "
        "supporting authentication and session tables, but the list below focuses on the business tables "
        "defined in the project models and the auth_user table referenced by foreign keys.",
    )
    add_caption(doc, "Table 4.1 List of Main Tables in market_db")
    rows = []
    for index, table in enumerate(TABLES, start=1):
        rows.append((index, table["name"], table["description"], table["pk"]))
    add_formatted_table(
        doc,
        ["No.", "Table Name", "Description", "Primary Key"],
        rows,
        [0.5, 1.6, 3.1, 1.3],
        font_size=9,
    )
    doc.add_page_break()


def build_data_dictionary(doc):
    doc.add_heading("5. Data Dictionary", level=1)
    add_body(
        doc,
        "The data dictionary documents every field in the main tables of market_db. The TYPE and LENGTH "
        "columns follow the MySQL data types generated by Django, while the CONSTRAINTS column lists primary "
        "keys, foreign keys, uniqueness, nullability, and default values.",
    )
    for index, table in enumerate(TABLES, start=1):
        doc.add_heading(f"5.{index} {table['name']}", level=2)
        add_caption(doc, f"Table 5.{index} Data Dictionary for {table['name']}")
        add_formatted_table(
            doc,
            ["FIELD", "DESCRIPTION", "TYPE", "LENGTH", "CONSTRAINTS"],
            table["fields"],
            [1.15, 2.05, 0.9, 0.75, 1.65],
            font_size=8.5,
        )
    doc.add_page_break()


def build_erd(doc):
    doc.add_heading("6. Entity-Relationship Diagram (ERD)", level=1)
    add_body(
        doc,
        "The entity-relationship diagram below presents the complete database structure of market_db, "
        "including all entities, attributes, primary keys, foreign keys, and relationship lines. Paste the "
        "final draw.io ERD export inside the bordered area.",
    )
    add_caption(doc, "Figure 6.1 Complete Entity-Relationship Diagram of market_db")
    add_placeholder_box(
        doc,
        "[INSERT / PASTE THE COMPLETE ERD HERE]",
        height=7.0,
        note="Use a portrait or landscape draw.io export that keeps all table labels readable.",
    )
    doc.add_page_break()


def build_entity_summary(doc):
    doc.add_heading("7. Entity Description & Relationship Summary", level=1)
    add_body(
        doc,
        "This section summarizes the role of each entity, its primary and foreign keys, and the cardinality "
        "of its relationships. It serves as the written counterpart of the ERD.",
    )

    doc.add_heading("7.1 Entity Description", level=2)
    add_caption(doc, "Table 7.1 Entity Description, Primary Keys, Foreign Keys, and Cardinality")
    add_formatted_table(
        doc,
        ["ENTITY", "PRIMARY KEY", "FOREIGN KEY(S)", "CARDINALITY", "DESCRIPTION"],
        ENTITY_ROWS,
        [1.15, 0.8, 1.35, 1.25, 1.95],
        font_size=8.5,
    )

    doc.add_heading("7.2 Relationship Summary", level=2)
    add_caption(doc, "Table 7.2 Relationship Summary and Cardinality")
    add_formatted_table(
        doc,
        ["RELATIONSHIP", "CARDINALITY", "DESCRIPTION"],
        RELATIONSHIP_ROWS,
        [2.0, 1.0, 3.5],
        font_size=9,
    )
    doc.add_page_break()


def build_sql_section(doc):
    doc.add_heading("8. SQL Statements", level=1)
    add_body(
        doc,
        "All statements below use MySQL syntax compatible with phpMyAdmin and the market_db database. Each "
        "item contains a problem statement, the exact SQL solution, a bordered placeholder for the "
        "phpMyAdmin output screenshot, and a results line. Replace each X with the actual number of rows "
        "returned or affected after executing the statement.",
    )

    sections = [
        ("8.1 SELECT Statements (30)", SELECT_QUERIES, "found"),
        ("8.2 INSERT Statements (10)", INSERT_QUERIES, "affected"),
        ("8.3 UPDATE Statements (10)", UPDATE_QUERIES, "affected"),
        ("8.4 DELETE Statements (5)", DELETE_QUERIES, "affected"),
        ("8.5 Subquery Statements (5)", SUBQUERY_QUERIES, "found"),
        ("8.6 JOIN Statements (10)", JOIN_QUERIES, "found"),
    ]

    first_query = True
    for section_title, queries, result_kind in sections:
        doc.add_heading(section_title, level=2)
        for index, query in enumerate(queries, start=1):
            if not first_query:
                doc.add_page_break()
            first_query = False

            query_heading = doc.add_paragraph()
            query_heading.paragraph_format.space_before = Pt(4)
            query_heading.paragraph_format.space_after = Pt(6)
            run = query_heading.add_run(f"Query {index}: {query['title']}")
            set_run_font(run, size=12, bold=True, color=NAVY)

            problem = doc.add_paragraph()
            problem.paragraph_format.space_after = Pt(4)
            run = problem.add_run("Problem Statement: ")
            set_run_font(run, size=10.5, bold=True)
            run = problem.add_run(query["problem"])
            set_run_font(run, size=10.5)

            solution = doc.add_paragraph()
            solution.paragraph_format.space_before = Pt(6)
            solution.paragraph_format.space_after = Pt(4)
            run = solution.add_run("Solution:")
            set_run_font(run, size=10.5, bold=True)

            add_code_block(doc, query["sql"])

            add_placeholder_box(
                doc,
                "[INSERT PHPMYADMIN OUTPUT SCREENSHOT HERE]",
                height=2.5,
                note="Paste the phpMyAdmin result grid or affected-rows message inside this box.",
            )

            result = doc.add_paragraph()
            result.paragraph_format.space_before = Pt(2)
            result.paragraph_format.space_after = Pt(4)
            run = result.add_run("Results: ")
            set_run_font(run, size=10.5, bold=True)
            if result_kind == "found":
                text = "X rows found."
            else:
                text = "X row(s) affected."
            run = result.add_run(text)
            set_run_font(run, size=10.5)


def main():
    doc = setup_document()
    build_title_page(doc)
    build_system_description(doc)
    build_design_sections(doc)
    build_list_of_tables(doc)
    build_data_dictionary(doc)
    build_erd(doc)
    build_entity_summary(doc)
    build_sql_section(doc)
    doc.save(OUTPUT_FILE)
    print(f"Created {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
