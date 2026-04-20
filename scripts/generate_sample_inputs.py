"""Generate small sample inputs (text) to exercise the pipeline.

These are NOT realistic scanned documents; they are lightweight fixtures
that let the Week-1 stub pipeline run end-to-end without heavy OCR/LLM.

Usage:
  python scripts/generate_sample_inputs.py

Outputs:
  data/fixtures/*.txt
"""

from __future__ import annotations

from pathlib import Path


SAMPLES: dict[str, str] = {
    "cheque_sample.txt": (
        "INDIAN CHEQUE\n"
        "Bank: HDFC BANK\n"
        "Branch: Andheri East, Mumbai\n"
        "IFSC: HDFC0000146\n"
        "Account No: 50100123456789\n"
        "Cheque No: 123456\n"
        "Date: 15/01/2026\n"
        "Pay: Rajesh Kumar\n"
        "Rupees: Fifty Four Thousand Three Hundred Twenty One Only\n"
        "Amount: 54,321.00\n"
        "Signature: PRESENT\n"
    ),
    "bank_statement_sample.txt": (
        "INDIAN BANK STATEMENT\n"
        "Account Holder: Swati Sharma\n"
        "Account Number: 123456789012\n"
        "Bank: State Bank of India\n"
        "Statement Period: 01-03-2026 to 31-03-2026\n\n"
        "Date        Description                   Debit      Credit     Balance\n"
        "01-03-2026  Opening Balance                                      50,000.00\n"
        "05-03-2026  Salary Credit                           80,000.00   130,000.00\n"
        "10-03-2026  UPI Payment - Grocery         2,350.00             127,650.00\n"
        "28-03-2026  Rent Transfer                25,000.00             102,650.00\n"
        "31-03-2026  Closing Balance                                     102,650.00\n"
    ),
    "salary_slip_sample.txt": (
        "INDIAN SALARY SLIP\n"
        "Employer: PaperTrail Technologies Pvt Ltd\n"
        "Employee Name: Anuj Verma\n"
        "Employee ID: PT-0142\n"
        "Pay Period: March 2026\n"
        "PAN: ABCDE1234F\n\n"
        "Earnings:\n"
        "  Basic: 50,000\n"
        "  HRA: 20,000\n"
        "  Special Allowance: 10,000\n"
        "Deductions:\n"
        "  PF: 6,000\n"
        "  Professional Tax: 200\n"
        "Net Pay: 73,800\n"
    ),
    "itr_form_sample.txt": (
        "INDIAN ITR FORM\n"
        "Assessment Year: 2026-27\n"
        "Name: Almichael Dsouza\n"
        "PAN: AAAAA9999A\n"
        "DOB: 01/01/1994\n"
        "Total Income: 12,34,567\n"
        "Tax Paid: 1,23,456\n"
        "Refund: 0\n"
        "Verification Date: 15/07/2026\n"
    ),
}


def main() -> None:
    out_dir = Path("data/fixtures")
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, content in SAMPLES.items():
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
