# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.model.document import Document
from frappe.desk.reportview import get_match_cond, get_filters_cond
from frappe.utils import comma_and

class ProgramEnrollment(Document):
	def validate(self):
		self.validate_duplication()
		if not self.student_name:
			self.student_name = frappe.db.get_value("Student", self.student, "title")
	
	def on_submit(self):
		self.update_student_joining_date()
		self.make_fee_records()
	
	def validate_duplication(self):
		enrollment = frappe.db.sql("""select name from `tabProgram Enrollment` where student= %s and program= %s 
			and academic_year= %s and docstatus<2 and name != %s""", (self.student, self.program, self.academic_year, self.name))
		if enrollment:
			frappe.throw(_("Student is already enrolled."))
	
	def update_student_joining_date(self):
		date = frappe.db.sql("select min(enrollment_date) from `tabProgram Enrollment` where student= %s", self.student)
		frappe.db.set_value("Student", self.student, "joining_date", date)
		
	def make_fee_records(self):
		from erpnext.schools.api import get_fee_components
		fee_list = []
		for d in self.fees:
			fee_components = get_fee_components(d.fee_structure)
			if fee_components:
				fees = frappe.new_doc("Fees")
				fees.update({
					"student": self.student,
					"academic_year": self.academic_year,
					"academic_term": d.academic_term,
					"fee_structure": d.fee_structure,
					"program": self.program,
					"due_date": d.due_date,
					"student_name": self.student_name,
					"program_enrollment": self.name,
					"components": fee_components
				})
				
				fees.save()
				fees.submit()
				fee_list.append(fees.name)
		if fee_list:
			fee_list = ["""<a href="#Form/Fees/%s" target="_blank">%s</a>""" % \
				(fee, fee) for fee in fee_list]
			msgprint(_("Fee Records Created - {0}").format(comma_and(fee_list)))

	def get_courses(self):
		return frappe.db.sql('''select course, course_name from `tabProgram Course` where parent = %s and required = 1''', (self.program), as_dict=1)


@frappe.whitelist()
def get_program_courses(doctype, txt, searchfield, start, page_len, filters):
	if filters.get('program'):
		return frappe.db.sql("""select course, course_name from `tabProgram Course`
			where  parent = %(program)s and course like %(txt)s {match_cond}
			order by
				if(locate(%(_txt)s, course), locate(%(_txt)s, course), 99999),
				idx desc,
				`tabProgram Course`.course asc
			limit {start}, {page_len}""".format(
				match_cond=get_match_cond(doctype),
				start=start,
				page_len=page_len), {
					"txt": "%{0}%".format(txt),
					"_txt": txt.replace('%', ''),
					"program": filters['program']
				})
