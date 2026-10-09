"""Kurs Manager — Web versiya (Flask + Bootstrap 5 dark theme)."""

from __future__ import annotations

import os
import sys
import csv
import io
from datetime import datetime
from pathlib import Path
from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
)

# Loyiha root'ini path ga qo'shish
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.database import DATABASE, DB_PATH, init_database
from services import (
    student_service,
    course_service,
    payment_service,
    report_service,
    backup_service,
    demo_data,
    test_service,
    reminder_service,
    attendance_service,
    group_service,
    monthly_payment_service,
)

app = Flask(__name__)
app.secret_key = "kurs-manager-web-secret-key"
app.config["DATABASE"] = str(DB_PATH)

# Boshlang'ich sozlash
init_database()
demo_data.seed()


def _format_money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ") + " so'm"


app.jinja_env.globals.update(
    format_money=_format_money,
    now=datetime.now,
)


# ===== DASHBOARD =====
@app.route("/")
def index():
    search = request.args.get("search", "").strip()
    stats = student_service.get_stats()
    trends = _trends(stats)
    students = student_service.list_students(search=search)
    recent = students[:10]
    return render_template("dashboard.html", stats=stats, trends=trends, students=recent)


# ===== STUDENTS =====
@app.route("/students")
def students_page():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "")
    course_id = request.args.get("course_id", "")
    cid = int(course_id) if course_id.isdigit() else None
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1
    per_page = 10
    try:
        month_filter = int(request.args.get("month", ""))
    except ValueError:
        month_filter = 0
    if not 1 <= month_filter <= 12:
        month_filter = 0
    if month_filter:
        # Shu oyda to'lov qilmaganlar: ✓ belgisi yo'qlar
        from datetime import date as _date

        from services import monthly_payment_service as _mp

        paid_ids = set(_mp.paid_student_ids(_date.today().year, month_filter))
        all_students = student_service.list_students(
            search=search, status=status or None, course_id=cid
        )
        filtered = [st for st in all_students if st["id"] not in paid_ids]
        total = len(filtered)
        pages = max((total + per_page - 1) // per_page, 1)
        page = min(page, pages)
        students = filtered[(page - 1) * per_page:page * per_page]
    else:
        total = student_service.count_students(search=search, status=status or None, course_id=cid)
        pages = max((total + per_page - 1) // per_page, 1)
        page = min(page, pages)
        students = student_service.list_students(
            search=search, status=status or None, course_id=cid,
            limit=per_page, offset=(page - 1) * per_page,
        )
    courses = course_service.all_courses()
    stats = student_service.get_stats()
    trends = _trends(stats)
    pagination = {"page": page, "pages": pages, "total": total, "per_page": per_page}
    return render_template(
        "students.html",
        students=students,
        courses=courses,
        groups=group_service.list_groups(),
        search=search,
        current_status=status,
        current_course=course_id,
        current_month=month_filter,
        stats=stats,
        trends=trends,
        pagination=pagination,
    )


def _trends(stats: dict) -> dict:
    total = stats.get("total", 0) or 0
    if not total:
        return {"total": 0, "paid": 0, "unpaid": 0}
    return {
        "total": 100,
        "paid": round(stats.get("paid", 0) * 100 / total),
        "unpaid": round(stats.get("unpaid", 0) * 100 / total),
    }


@app.route("/students/create", methods=["POST"])
def student_create():
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    course_id = request.form.get("course_id")
    # To'lov holati faqat «To'lovlar» bo'limidan boshqariladi — yangi o'quvchi default: to'lanmagan
    payment_status = request.form.get("payment_status", "unpaid")
    note = request.form.get("note", "").strip()
    try:
        total_price = float((request.form.get("total_price") or "0").replace(" ", ""))
        paid_amount = float((request.form.get("paid_amount") or "0").replace(" ", ""))
    except ValueError:
        flash("Summani to'g'ri kiriting.", "error")
        return redirect(url_for("students_page"))
    if payment_status not in ("paid", "unpaid"):
        payment_status = "unpaid"

    cid = int(course_id) if course_id and course_id.isdigit() else None

    from utils import validators
    err = validators.validate_full_name(full_name)
    if err:
        flash(err, "error")
        return redirect(url_for("students_page"))
    err = validators.validate_phone(phone)
    if err:
        flash(err, "error")
        return redirect(url_for("students_page"))
    err = validators.validate_course_selected(cid)
    if err:
        flash(err, "error")
        return redirect(url_for("students_page"))

    created_at = _parse_reg_date(request.form)
    group_ids = _parse_group_ids(request.form)
    grade = request.form.get("grade", "").strip()

    try:
        new_id = student_service.create_student(
            full_name, phone, cid, payment_status, note,
            created_at=created_at,
            total_price=total_price, paid_amount=paid_amount,
            grade=grade,
        )
        failed = 0
        for gid in group_ids:
            try:
                group_service.add_member(gid, new_id)
            except Exception:
                failed += 1
        if failed:
            flash("O'quvchi qo'shildi, lekin %d ta guruhga qo'shib bo'lmadi." % failed, "error")
        else:
            flash("Yangi o'quvchi qo'shildi.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(request.form.get("next") or url_for("students_page"))


def _parse_group_ids(form) -> list[int]:
    """Formadagi group_ids checkboxlarini o'qiydi."""
    ids = []
    for raw in form.getlist("group_ids"):
        try:
            gid = int(raw)
        except (TypeError, ValueError):
            continue
        if gid > 0:
            ids.append(gid)
    return sorted(set(ids))


def _parse_start_day(raw) -> datetime:
    """Kelgan kuni (1-31) -> shu oy sanasi. Xato bo'lsa bugun."""
    from calendar import monthrange

    today = datetime.now()
    try:
        day = int(raw)
    except (TypeError, ValueError):
        return today
    max_day = monthrange(today.year, today.month)[1]
    day = max(1, min(day, max_day))
    return datetime(today.year, today.month, day)


def _parse_reg_date(form) -> datetime:
    """To'liq kelgan sana (kun/oy/yil). Xato bo'lsa eski start_day mantiqi."""
    from calendar import monthrange

    today = datetime.now()
    try:
        day = int(form.get("reg_day"))
        month = int(form.get("reg_month"))
        year = int(form.get("reg_year"))
    except (TypeError, ValueError):
        return _parse_start_day(form.get("start_day"))
    if not (1 <= month <= 12 and 2000 <= year <= 2100):
        return _parse_start_day(form.get("start_day"))
    max_day = monthrange(year, month)[1]
    day = max(1, min(day, max_day))
    return datetime(year, month, day)


@app.route("/students/quick-create", methods=["POST"])
def student_quick_create():
    """Faqat F.I.Sh bilan tez qo'shish (Davomat bo'limi uchun).

    Telefon bo'sh, kurs — birinchi faol kurs, holat — to'lanmagan.
    """
    from utils import validators

    full_name = request.form.get("full_name", "").strip()
    err = validators.validate_full_name(full_name)
    if err:
        flash(err, "error")
        return redirect(request.form.get("next") or url_for("attendance_page"))

    courses = course_service.all_courses()
    active = [c for c in courses if c["active"]]
    cid = (active[0]["id"] if active else (courses[0]["id"] if courses else None))

    try:
        student_service.create_student(full_name, "", cid, "unpaid", "")
        flash("Yangi o'quvchi qo'shildi.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(request.form.get("next") or url_for("attendance_page"))


@app.route("/students/<int:sid>/update", methods=["POST"])
def student_update(sid):
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    course_id = request.form.get("course_id")
    note = request.form.get("note", "").strip()
    # To'lov holati formadan o'zgartirilmaydi — faqat «To'lovlar» bo'limi boshqaradi
    current = student_service.get_student(sid) or {}
    payment_status = current.get("payment_status") or "unpaid"
    try:
        total_price = float((request.form.get("total_price") or "0").replace(" ", ""))
        paid_amount = float((request.form.get("paid_amount") or "0").replace(" ", ""))
    except ValueError:
        flash("Summani to'g'ri kiriting.", "error")
        return redirect(url_for("students_page"))

    cid = int(course_id) if course_id and course_id.isdigit() else None

    from utils import validators
    err = validators.validate_full_name(full_name)
    if err:
        flash(err, "error")
        return redirect(url_for("students_page"))
    err = validators.validate_phone(phone)
    if err:
        flash(err, "error")
        return redirect(url_for("students_page"))

    created_day = _parse_created_day(request.form.get("start_day"))
    if created_day is None and (request.form.get("start_day") not in (None, "")):
        flash("Kunni to'g'ri kiriting (1-31).", "error")
        return redirect(url_for("students_page"))
    group_ids = _parse_group_ids(request.form)
    grade = request.form.get("grade", "").strip()

    try:
        student_service.update_student(
            sid, full_name, phone, cid, payment_status, note,
            paid_months=None, created_day=created_day,
            total_price=total_price, paid_amount=paid_amount,
            grade=grade,
        )
        group_service.set_student_groups(sid, group_ids)
        flash("O'quvchi yangilandi.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("students_page"))


def _parse_created_day(raw) -> int | None:
    """Tahrirlashdagi kun: bo'sh bo'lsa None (tegilmaydi)."""
    if raw is None or str(raw).strip() == "":
        return None
    try:
        day = int(raw)
    except (TypeError, ValueError):
        return None
    if 1 <= day <= 31:
        return day
    return None


@app.route("/students/<int:sid>/delete", methods=["POST"])
def student_delete(sid):
    try:
        student_service.delete_student(sid)
        flash("O'quvchi o'chirildi.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("students_page"))


@app.route("/api/groups")
def api_groups():
    return jsonify(group_service.list_groups())


@app.route("/api/student/<int:sid>")
def api_student(sid):
    st = student_service.get_student(sid)
    if not st:
        return jsonify({"error": "topilmadi"}), 404
    payments = payment_service.list_by_student(sid)
    st["payments"] = payments
    return jsonify(st)


# ===== COURSES (o'chirilgan — dastur faqat "Kimyo fani" kursi uchun) =====
@app.route("/courses")
def courses_page():
    return redirect(url_for("index"))


# ===== PAYMENTS (oylik jurnal) =====
@app.route("/payments")
def payments_page():
    from datetime import date as _date

    search = request.args.get("search", "").strip()
    try:
        year = int(request.args.get("year", _date.today().year))
    except ValueError:
        year = _date.today().year
    year = max(2000, min(year, 2100))
    students, matrix = monthly_payment_service.get_matrix(year, search=search)
    stats = monthly_payment_service.matrix_stats(matrix)
    return render_template(
        "payments.html",
        students=students,
        matrix=matrix,
        month_pairs=monthly_payment_service.ordered_months(),
        year=year,
        search=search,
        stats=stats,
    )


@app.route("/api/monthly-payments/set", methods=["POST"])
def api_monthly_payment_set():
    try:
        data = request.get_json(force=True)
        student_id = int(data.get("student_id"))
        year = int(data.get("year"))
        month = int(data.get("month"))
        raw = data.get("paid")
        paid = None if raw is None else bool(raw)
        try:
            amount = float(str(data.get("amount") or "0").replace(" ", ""))
        except (ValueError, TypeError):
            amount = 0.0
        if paid is True and not amount > 0:
            return jsonify({"error": "To'langan summani kiriting."}), 400
        state = monthly_payment_service.set_status(
            student_id, year, month, paid, amount
        )
        _, matrix = monthly_payment_service.get_matrix(year)
        stats = monthly_payment_service.matrix_stats(matrix)
        return jsonify({
            "state": state,
            "paid": stats["paid"],
            "unpaid": stats["unpaid"],
            "collected": stats["collected"],
        })
    except (ValueError, TypeError, KeyError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/monthly-payment/detail")
def api_monthly_payment_detail():
    try:
        student_id = int(request.args.get("student_id"))
        year = int(request.args.get("year"))
        month = int(request.args.get("month"))
        return jsonify(monthly_payment_service.get_cell_detail(student_id, year, month))
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ===== REPORTS =====
@app.route("/reports")
def reports_page():
    from services import activity_service as _act

    data = report_service.summary()
    trends = _trends(data)
    journal = _act.list_logs(limit=100)
    return render_template("reports.html", data=data, trends=trends, journal=journal)


@app.route("/reports/export")
def reports_export():
    try:
        pdf_path = report_service.export_pdf(None)
        return send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"kurs_manager_hisobot_{datetime.now():%Y%m%d}.pdf",
        )
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for("reports_page"))


# ===== SETTINGS (o'chirilgan) =====
# Sozlamalar bo'limi olib tashlandi.


# ===== TEST NATIJALARI =====
@app.route("/tests")
def tests_page():
    search = request.args.get("search", "").strip()
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1
    per_page = 10
    total = test_service.count_results(search=search)
    pages = max((total + per_page - 1) // per_page, 1)
    page = min(page, pages)
    results = test_service.list_results(
        search=search, limit=per_page, offset=(page - 1) * per_page
    )
    students = student_service.list_students()
    pagination = {"page": page, "pages": pages, "total": total, "per_page": per_page}
    return render_template(
        "tests.html",
        results=results,
        students=students,
        search=search,
        pagination=pagination,
    )


@app.route("/tests/create", methods=["POST"])
def test_create():
    try:
        student_id = request.form.get("student_id")
        topic = request.form.get("topic", "").strip()
        total_q = int(request.form.get("total_questions") or 0)
        correct = int(request.form.get("correct_answers") or 0)
        date_str = request.form.get("result_date", "")
        note = request.form.get("note", "").strip()
        if not student_id:
            flash("O'quvchini tanlang.", "error")
            return redirect(url_for("tests_page"))
        dt = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
        test_service.create_result(int(student_id), topic, total_q, correct, dt, note)
        flash("Yangi test natijasi qo'shildi.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("tests_page"))


@app.route("/tests/<int:rid>/update", methods=["POST"])
def test_update(rid):
    try:
        topic = request.form.get("topic", "").strip()
        total_q = int(request.form.get("total_questions") or 0)
        correct = int(request.form.get("correct_answers") or 0)
        date_str = request.form.get("result_date", "")
        note = request.form.get("note", "").strip()
        dt = datetime.strptime(date_str, "%Y-%m-%d") if date_str else None
        test_service.update_result(rid, topic, total_q, correct, dt, note)
        flash("Natija yangilandi.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("tests_page"))


@app.route("/tests/<int:rid>/delete", methods=["POST"])
def test_delete(rid):
    try:
        test_service.delete_result(rid)
        flash("Natija o'chirildi.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("tests_page"))


@app.route("/api/test/<int:rid>")
def api_test(rid):
    t = test_service.get_result(rid)
    if not t:
        return jsonify({"error": "topilmadi"}), 404
    t["result_date_str"] = t["result_date"].strftime("%Y-%m-%d")
    return jsonify(t)


# ===== ESLATMALAR =====
@app.route("/reminders")
def reminders_page():
    reminders = reminder_service.list_reminders()
    return render_template("reminders.html", reminders=reminders)


def _parse_remind_at(value: str) -> datetime:
    value = (value or "").strip()
    if not value:
        raise ValueError("Sana va vaqtni belgilang.")
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError("Sana va vaqt noto'g'ri formatda.")


@app.route("/reminders/create", methods=["POST"])
def reminder_create():
    try:
        title = request.form.get("title", "")
        note = request.form.get("note", "")
        remind_at = _parse_remind_at(request.form.get("remind_at", ""))
        reminder_service.create_reminder(title, note, remind_at)
        flash("Yangi eslatma qo'shildi.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("reminders_page"))


@app.route("/reminders/<int:rid>/update", methods=["POST"])
def reminder_update(rid):
    try:
        title = request.form.get("title", "")
        note = request.form.get("note", "")
        raw = request.form.get("remind_at", "")
        remind_at = _parse_remind_at(raw) if raw.strip() else None
        reminder_service.update_reminder(rid, title, note, remind_at)
        flash("Eslatma yangilandi.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("reminders_page"))


@app.route("/reminders/<int:rid>/delete", methods=["POST"])
def reminder_delete(rid):
    try:
        reminder_service.delete_reminder(rid)
        flash("Eslatma o'chirildi.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("reminders_page"))


@app.route("/reminders/<int:rid>/toggle", methods=["POST"])
def reminder_toggle(rid):
    try:
        r = reminder_service.get_reminder(rid)
        if r:
            reminder_service.set_done(rid, not r["is_done"])
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("reminders_page"))


@app.route("/api/payments/due")
def api_payments_due():
    """Muddati yaqinlashgan/kechikkan to'lovlar (har biri bir marta)."""
    from services.due_service import get_payment_dues

    return jsonify(get_payment_dues())


@app.route("/logo.png")
def logo():
    return send_file(str(ROOT / "image" / "logotip.png"), mimetype="image/png")


@app.route("/api/reminders/due")
def api_reminders_due():
    return jsonify(reminder_service.get_due())


@app.route("/api/reminders/pending-count")
def api_reminders_pending_count():
    return jsonify({"count": reminder_service.pending_count()})


@app.route("/api/reminder/<int:rid>")
def api_reminder(rid):
    r = reminder_service.get_reminder(rid)
    if not r:
        return jsonify({"error": "topilmadi"}), 404
    return jsonify(r)


# ===== DAVOMAT =====
@app.route("/attendance")
def attendance_page():
    try:
        week_offset = int(request.args.get("week", 0))
    except ValueError:
        week_offset = 0
    week_offset = max(min(week_offset, 52), -52)
    dates = attendance_service.week_dates(week_offset)
    students, matrix, stats = attendance_service.get_matrix(dates)
    courses = course_service.all_courses()
    default_course = courses[0] if courses else None
    date_infos = [
        {
            "iso": d.isoformat(),
            "day": d.strftime("%d.%m"),
            "wd": attendance_service.WEEKDAYS[d.weekday()],
            "is_today": d == __import__("datetime").date.today(),
        }
        for d in dates
    ]
    return render_template(
        "attendance.html",
        students=students,
        matrix=matrix,
        stats=stats,
        date_infos=date_infos,
        week_offset=week_offset,
        week_title=f"{dates[0].strftime('%d.%m')} — {dates[-1].strftime('%d.%m.%Y')}",
        default_course=default_course,
    )


@app.route("/api/attendance/set", methods=["POST"])
def api_attendance_set():
    try:
        data = request.get_json(force=True)
        student_id = int(data.get("student_id"))
        att_date = datetime.strptime(data.get("date", ""), "%Y-%m-%d").date()
        raw = data.get("present")
        present = None if raw is None else bool(raw)
        result = attendance_service.set_attendance(student_id, att_date, present)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ===== GURUHLAR =====
@app.route("/groups")
def groups_page():
    groups = group_service.list_groups()
    return render_template("groups.html", groups=groups)


@app.route("/groups/create", methods=["POST"])
def group_create():
    try:
        group_service.create_group(request.form.get("name", ""))
        flash("Yangi guruh ochildi.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("groups_page"))


@app.route("/groups/<int:gid>/update", methods=["POST"])
def group_update(gid):
    try:
        group_service.update_group(gid, request.form.get("name", ""))
        flash("Guruh nomi saqlandi.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("groups_page"))


@app.route("/groups/<int:gid>/delete", methods=["POST"])
def group_delete(gid):
    try:
        group_service.delete_group(gid)
        flash("Guruh o'chirildi.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("groups_page"))


@app.route("/groups/<int:gid>/members")
def group_members_page(gid):
    group = group_service.get_group(gid)
    if not group:
        flash("Guruh topilmadi.", "error")
        return redirect(url_for("groups_page"))
    members = group_service.list_members(gid)
    available = group_service.available_students(gid)
    other_groups = [g for g in group_service.list_groups() if g["id"] != gid]
    return render_template(
        "group_members.html", group=group, members=members,
        available=available, other_groups=other_groups,
    )


@app.route("/groups/<int:gid>/move-member/<int:sid>", methods=["POST"])
def group_move_member(gid, sid):
    try:
        target = request.form.get("target_group_id")
        if not target:
            flash("Guruh tanlanmagan.", "error")
            return redirect(url_for("group_members_page", gid=gid))
        target_name = group_service.move_member(gid, int(target), sid)
        flash("O'quvchi «%s» guruhiga ko'chirildi." % target_name, "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("group_members_page", gid=gid))


@app.route("/groups/<int:gid>/add-member", methods=["POST"])
def group_add_member(gid):
    try:
        student_id = request.form.get("student_id")
        if not student_id:
            flash("O'quvchini tanlang.", "error")
            return redirect(url_for("group_members_page", gid=gid))
        group_service.add_member(gid, int(student_id))
        flash("O'quvchi guruhga qo'shildi.", "success")
    except ValueError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("group_members_page", gid=gid))


@app.route("/groups/<int:gid>/remove-member/<int:sid>", methods=["POST"])
def group_remove_member(gid, sid):
    try:
        group_service.remove_member(gid, sid)
        flash("O'quvchi guruhdan chiqarildi.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("group_members_page", gid=gid))


# ===== API =====
@app.route("/api/stats")
def api_stats():
    return jsonify(student_service.get_stats())


# ===== MAIN =====
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)