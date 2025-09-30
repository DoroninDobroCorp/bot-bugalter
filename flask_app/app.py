# app.py (переработанная версия)

from flask import Flask, render_template, redirect, url_for, abort, request, make_response, g, jsonify
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from datetime import datetime as dt, date
import logging

from data.models import *
from data.config import async_session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'token'
logging.basicConfig(level=logging.INFO)


@app.before_request
async def load_user_and_check_token():
	if request.path.startswith('/login'):
		return

	access_token = request.cookies.get('access_token')
	if not access_token:
		return render_template('token_invalid.html', token='отсутствует'), 401

	# async with async_session() as session:
	# 	stmt = select(Employee).options(
	# 		selectinload(Employee.token).selectinload(Employee.admins_employee)
	# 	).where(Employee.token == access_token)
	# 	employee = (await session.execute(stmt)).scalar_one_or_none()
	
	employee = await Employee.get(token=access_token)

	if not employee:
		response = make_response(render_template('token_invalid.html', token=access_token))
		response.set_cookie('access_token', '', expires=0)
		return response

	if not employee.token:
		response = make_response(render_template('token_expired.html', token=access_token))
		response.set_cookie('access_token', '', expires=0)
		return response

	g.employee = employee

	admin = await Admin.get(employee_id=employee.id)
	g.is_admin = (admin is not None)

	admin_only_paths = ['/matches', '/reports', '/match/'] 
	if any(request.path.startswith(p) for p in admin_only_paths) and not g.is_admin:
		return render_template('access_denied.html'), 403


def render(template, **kwargs):
	return render_template(template, **kwargs, is_admin=g.get('is_admin', False))


@app.route('/')
async def home():
	return render('base.html')


@app.route('/matches', methods=['GET', 'POST'])
async def matches():
	filter_date = None
	filter_source = None
	search_performed = request.method == 'POST'
	
	if request.method == 'POST':
		date_str = request.form.get('filter_date')
		if date_str:
			try:
				filter_date = dt.strptime(date_str, '%Y-%m-%d').date()
			except ValueError:
				pass
		filter_source = request.form.get('filter_source')
	
	async with async_session() as session:
		# Get sources for filter dropdown
		sources = (await session.execute(select(Source).where(Source.is_deleted == False))).scalars().all()
		
		stmt_report_matches = (
			select(Report.match_id)
			.where(
				Report.is_deleted == False,
				Report.is_employee_checked == True,
				Report.is_admin_checked == False
			)
		)
		
		# Apply filters if provided
		if filter_date:
			stmt_report_matches = stmt_report_matches.where(func.date(Report.date) == filter_date)
		if filter_source:
			stmt_report_matches = stmt_report_matches.where(Report.source_id == int(filter_source))
		
		stmt_report_matches = stmt_report_matches.distinct()
		report_match_ids = (await session.execute(stmt_report_matches)).scalars().all()
		
		if not report_match_ids:
			return render('matches.html', matches=[], sources=sources, 
						 filter_date=filter_date.isoformat() if filter_date else '', 
						 filter_source=filter_source or '', search_performed=search_performed)

		stmt_canonical_matches = (
			select(Match.id, Match.canonical_id)
			.where(Match.id.in_(report_match_ids))
		)
		canonical_matches_result = await session.execute(stmt_canonical_matches)
		
		parent_match_ids = set()
		for id, canonical_id in canonical_matches_result:
			parent_match_ids.add(canonical_id if canonical_id else id)

		stmt_final_matches = (
			select(Match)
			.where(Match.id.in_(parent_match_ids))
			.options(
				selectinload(Match.children_matches).selectinload(Match.reports),
				selectinload(Match.reports)
			)
		)
		
		final_matches = (await session.execute(stmt_final_matches)).unique().scalars().all()

		ready_matches = []
		for match in final_matches:
			unchecked_reports = [r for r in match.reports if r.is_employee_checked and not r.is_admin_checked and not r.is_deleted]
			for child in match.children_matches:
				unchecked_reports.extend([r for r in child.reports if r.is_employee_checked and not r.is_admin_checked and not r.is_deleted])

			if unchecked_reports:
				# Filter by date and source if needed
				if filter_date:
					unchecked_reports = [r for r in unchecked_reports if r.date.date() == filter_date]
				if filter_source:
					unchecked_reports = [r for r in unchecked_reports if str(r.source_id) == filter_source]
				
				if unchecked_reports:
					match.unchecked_reports = unchecked_reports
					# Calculate date range for display
					dates = [r.date for r in unchecked_reports if r.date]
					if dates:
						match.date_min = min(dates)
						match.date_max = max(dates)
					ready_matches.append(match)

	return render('matches.html', matches=ready_matches, sources=sources,
				 filter_date=filter_date.isoformat() if filter_date else '',
				 filter_source=filter_source or '', search_performed=search_performed)

@app.route('/bookmakers')
async def bookmakers():
	async with async_session() as session:
		reports_subquery = (
			select(Report.bookmaker_id)
			.where(
				Report.is_admin_checked == False,
				Report.is_employee_checked == False,
				Report.is_deleted == False
			)
		)
		if not g.is_admin:
			reports_subquery = reports_subquery.where(Report.nickname == g.employee.username)
		
		reports_subquery = reports_subquery.distinct().subquery()

		stmt = (
			select(Bookmaker)
			.join(reports_subquery, Bookmaker.id == reports_subquery.c.bookmaker_id)
			.options(
				selectinload(Bookmaker.country),
				selectinload(Bookmaker.reports)
			)
		)
		
		bks = (await session.execute(stmt)).unique().scalars().all()

		for bookmaker in bks:
			if g.is_admin:
				bookmaker.reports_no_result = [r for r in bookmaker.reports if not r.is_admin_checked and not r.is_employee_checked and not r.is_deleted]
			else:
				bookmaker.reports_no_result = [r for r in bookmaker.reports if not r.is_admin_checked and not r.is_employee_checked and not r.is_deleted and r.nickname == g.employee.username]
			
	return render('bookmakers.html', bookmakers=bks)


@app.route('/bookmaker/<bookmaker_id>')
async def bookmaker_detail(bookmaker_id):
	async with async_session() as session:
		base_stmt = select(Report).where(
			Report.bookmaker_id == bookmaker_id,
			Report.is_deleted == False,
			Report.is_employee_checked == False,
			Report.is_admin_checked == False
		)
		if not g.is_admin:
			base_stmt = base_stmt.where(Report.nickname == g.employee.username)

		reports = (
			await session.execute(base_stmt.options(selectinload(Report.match)))
		).unique().scalars().all()
		
		bookmaker = await session.get(
			Bookmaker, 
			bookmaker_id, 
			options=[selectinload(Bookmaker.country)]
		)
		if not bookmaker:
			abort(404)

	return render('bookmaker_detail.html', bookmaker=bookmaker, reports=reports)


@app.route('/match/<match_id>')
async def match_detail(match_id):
	async with async_session() as session:
		match = await session.get(Match, match_id)
		if not match:
			abort(404)

		child_ids_stmt = select(Match.id).where(Match.canonical_id == match.id)
		child_ids = (await session.execute(child_ids_stmt)).scalars().all()
		
		all_match_ids = [match.id] + child_ids

		reports_stmt = (
			select(Report)
			.where(
				Report.match_id.in_(all_match_ids),
				Report.is_deleted == False,
				Report.is_admin_checked == False,
				Report.is_employee_checked == True
			)
			.options(
				selectinload(Report.bookmaker).selectinload(Bookmaker.country),
				selectinload(Report.employees),
				selectinload(Report.source),
				selectinload(Report.country)
			)
		)
		reports = (await session.execute(reports_stmt)).unique().scalars().all()

	return render('match_detail.html', match=match, reports=reports)


@app.route('/api/search_matches')
async def search_matches():
	if not g.get('employee'):
		return jsonify(error="Unauthorized"), 401
		
	query = request.args.get('q', '').strip()
	if len(query) < 2:
		return jsonify([])

	async with async_session() as session:
		stmt = (
			select(Match.id, Match.name)
			.where(
				Match.name.ilike(f'%{query}%'),
				Match.is_active == True,
				Match.canonical_id == None
			)
			.limit(15)
		)
		
		results = await session.execute(stmt)
		matches_list = [{'id': id, 'text': name} for id, name in results]

	return jsonify(matches_list)


@app.route('/reports', methods=['GET', 'POST'])
async def reports():
	selected_date = date.today()
	reports_list = []

	if request.method == 'POST':
		date_str = request.form.get('report_date')
		if date_str:
			try:
				selected_date = dt.strptime(date_str, '%Y-%m-%d').date()
			except ValueError:
				selected_date = date.today()

	async with async_session() as session:
		stmt = (
			select(Report)
			.where(
				func.date(Report.date) == selected_date,
				Report.is_deleted == False
			)
			.options(
				selectinload(Report.match), 
				selectinload(Report.bookmaker), 
				selectinload(Report.employees)
			)
			.order_by(Report.date.desc())
		)
		reports_list = (await session.execute(stmt)).unique().scalars().all()

	return render(
		'reports.html', 
		reports=reports_list, 
		selected_date=selected_date.isoformat(),
		search_performed=(request.method == 'POST')
	)


@app.route('/report/<int:report_id>', methods=['GET', 'POST'])
async def edit_report(report_id):
	async with async_session() as session:
		report = await session.get(Report, report_id, options=[
			selectinload(Report.employees),
			selectinload(Report.source),
			selectinload(Report.match).selectinload(Match.canonical_match)
		])
		if not report:
			abort(404)

		sources = (await session.execute(select(Source).where(Source.is_deleted == False))).scalars().all()
		countries = (await session.execute(select(Country).where(Country.is_deleted == False))).scalars().all()
	
	employees = ', '.join([empl.second_name for empl in report.employees])
	error = app.config.get('error')
	app.config['error'] = None

	return render(
		'edit_report.html',
		report=report, error=error,
		sources=sources, countries=countries,
		employees=employees
	)


@app.route('/report/<int:report_id>/confirm_edit', methods=['POST'])
async def confirm_report_edit(report_id):
	try:
		date_val = dt.strptime(request.form.get('date'), "%Y-%m-%d %H:%M:%S")
		source_id = int(request.form.get('source'))
		country_id = int(request.form.get('country'))
		bookmaker_id = int(request.form.get('bookmaker'))
		match_id = request.form.get('match')
		coefficient = float(request.form.get('coefficient'))
		bet_amount = float(request.form.get('stake'))
		return_amount = float(request.form.get('refund'))
		empl_names_str = request.form.get('employees', '').strip()
		
		if not empl_names_str:
			raise Exception("Поле 'Сотрудники' не может быть пустым.")
		
		empl_names = [name.strip() for name in empl_names_str.split(',') if name.strip()]

		async with async_session() as session:
			found_employees_stmt = select(Employee).where(Employee.second_name.in_(empl_names))
			found_employees = (await session.execute(found_employees_stmt)).scalars().all()

			found_names = {emp.second_name for emp in found_employees}
			not_found_names = set(empl_names) - found_names

			if not_found_names:
				raise Exception("Не найдены сотрудники: " + ', '.join(not_found_names))
			
			report = await session.get(Report, report_id)
			if not report:
				abort(404)

			report.date = date_val
			report.date_str = date_val.strftime("%d.%m.%Y")
			report.status = 'Обычный' if len(empl_names) == 1 else 'Основной'
			report.source_id = source_id
			report.country_id = country_id
			report.bookmaker_id = bookmaker_id
			report.match_id = match_id
			report.nickname = found_employees[0].username
			report.bet_amount = bet_amount
			report.return_amount = return_amount
			report.coefficient = coefficient
			report.is_error = request.form.get('error') is not None
			report.is_over = request.form.get('over') is not None

			delete_stmt = delete(ReportEmployee).where(ReportEmployee.report_id == report.id)
			await session.execute(delete_stmt)
			
			for employee in found_employees:
				session.add(ReportEmployee(report_id=report.id, employee_id=employee.id))
				
			await session.commit()
			
	except Exception as e:
		app.config['error'] = e
		return redirect(url_for('edit_report', report_id=report_id))
	
	return redirect(url_for('match_detail', match_id=match_id))


@app.route('/report/<int:report_id>/delete', methods=['POST'])
async def delete_report(report_id):
	async with async_session() as session:
		report = await session.get(Report, report_id)
		if not report:
			abort(404)
		report.is_deleted = True
		match_id = report.match_id
		await session.commit()
	return redirect(url_for('match_detail', match_id=match_id))


@app.route('/report/<int:report_id>/mark_checked', methods=['POST'])
async def mark_single_checked(report_id):
	async with async_session() as session:
		report = await session.get(Report, report_id)
		if not report:
			abort(404)
		report.is_admin_checked = True
		match_id = report.match_id
		await session.commit()
	return redirect(url_for('match_detail', match_id=match_id))


@app.route('/report/<int:report_id>/confirm_coef/', methods=['POST'])
async def confirm_report_coef(report_id):
	report_result = request.form.get('report_result')
	return_amount = float(request.form.get('return_amount').replace(',', '.'))

	async with async_session() as session:
		report = await session.get(Report, report_id, options=[selectinload(Report.bookmaker)])
		if not report:
			abort(404)

		if report_result == "win":
			report.is_employee_checked = True
			report.return_amount = report.coefficient * report.bet_amount
		elif report_result == "lose":
			report.is_employee_checked = True
			report.return_amount = 0
		elif report_result == "return":
			report.is_employee_checked = True
			report.return_amount = return_amount
		
		bookmaker_id = report.bookmaker.id
		await session.commit()

	return redirect(url_for('bookmaker_detail', bookmaker_id=bookmaker_id))


@app.route('/match/<match_id>/mark_checked', methods=['POST'])
async def mark_all_checked(match_id):
	async with async_session() as session:
		match = await session.get(Match, match_id)
		if not match:
			abort(404)
		
		# Get child match IDs
		child_ids_stmt = select(Match.id).where(Match.canonical_id == match_id)
		child_ids = (await session.execute(child_ids_stmt)).scalars().all()
		all_match_ids = [match_id] + child_ids
		
		stmt = (
			update(Report)
			.where(
				Report.match_id.in_(all_match_ids),
				Report.is_employee_checked == True,
				Report.is_admin_checked == False,
				Report.is_deleted == False
			)
			.values(is_admin_checked=True)
		)
		await session.execute(stmt)
		await session.commit()

	return redirect(url_for("matches"))


@app.route('/login')
async def login():
	token = request.args.get('token')
	to = request.args.get('to')
	if not token or not to:
		abort(400)
	
	employee = await Employee.get(token=token)
	if not employee or not employee.token:
		return render_template('token_invalid.html', token=token)

	response = redirect(url_for(('matches' if to == '1' else 'bookmakers')))
	response.set_cookie('access_token', token, secure=True, samesite='None', domain=None)
	return response


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8180, debug=True)
