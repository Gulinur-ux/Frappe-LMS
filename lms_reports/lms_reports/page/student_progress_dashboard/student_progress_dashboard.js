frappe.pages['student-progress-dashboard'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Student Progress Dashboard',
		single_column: true
	});

	page.set_title('Student Progress Dashboard');
	page.set_indicator('Real-Time', 'green');

	// Add Course Filter
	let courseFilter = page.add_field({
		fieldname: 'course',
		label: __('Course'),
		fieldtype: 'Link',
		options: 'LMS Course',
		change: function () {
			refresh_dashboard();
		}
	});

	// Add Student Filter
	let studentFilter = page.add_field({
		fieldname: 'student',
		label: __('Student'),
		fieldtype: 'Link',
		options: 'User',
		change: function () {
			refresh_dashboard();
		}
	});

	// Add Lesson Filter
	let lessonFilter = page.add_field({
		fieldname: 'lesson',
		label: __('Lesson'),
		fieldtype: 'Link',
		options: 'Course Lesson',
		get_query: function () {
			let course = courseFilter.get_value();
			if (course) {
				return {
					filters: {
						"course": course
					}
				};
			}
		},
		change: function () {
			refresh_dashboard();
		}
	});

	function refresh_dashboard() {
		render_dashboard(
			page,
			courseFilter.get_value(),
			studentFilter.get_value(),
			lessonFilter.get_value()
		);
	}

	// Render default view (or ask to select course)
	$(wrapper).find('.layout-main-section').append(`
		<div class="dashboard-content" style="padding: 20px;">
			<div class="row">
				<div class="col-md-12 text-center text-muted" id="placeholder">
					<h4>Please select a course to view progress</h4>
				</div>
			</div>
			
			<div id="stats-section" style="display:none;">
				<div class="row mb-4">
					<div class="col-md-6">
						<div class="dashboard-stat-box" style="background:var(--card-bg); padding:20px; border-radius:8px; border:1px solid var(--border-color);">
							<h5 class="text-muted">Total Students</h5>
							<h2 id="total-students">0</h2>
						</div>
					</div>
					<div class="col-md-6">
						<div class="dashboard-stat-box" style="background:var(--card-bg); padding:20px; border-radius:8px; border:1px solid var(--border-color);">
							<h5 class="text-muted">Total Lessons</h5>
							<h2 id="total-lessons">0</h2>
						</div>
					</div>
				</div>

				<div class="row">
					<div class="col-md-12">
						<div class="card">
							<div class="card-header">
								<h5 class="card-title">Student Progress Details</h5>
							</div>
							<div class="card-body">
								<div id="students-table"></div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	`);
}

function render_dashboard(page, course, student, lesson) {
	if (!course) {
		$('#placeholder').show();
		$('#stats-section').hide();
		return;
	}

	$('#placeholder').hide();
	$('#stats-section').show();

	frappe.call({
		method: 'lms_reports.lms_reports.api.get_course_progress_summary',
		args: {
			course: course,
			student: student,
			lesson: lesson
		},
		callback: function (r) {
			if (r.message) {
				update_dashboard(r.message, lesson);
			}
		}
	});
}

function update_dashboard(data, lesson_filter) {
	// Update Summary Stats
	$('#total-students').text(data.total_students);
	$('#total-lessons').text(data.lesson_count);

	// Dynamic Header based on filter

	// Dynamic Header based on filter
	let progress_header = lesson_filter ? "Lesson Progress" : "Overall Progress";

	// Render Students Table
	let html = `
		<table class="table table-bordered table-hover">
			<thead>
				<tr>
					<th>Student</th>
					<th>${progress_header}</th>
					<th>Completed Lessons</th>
					<th>Video Speed</th>
					<th>Recent Activity</th>
				</tr>
			</thead>
			<tbody>
	`;

	data.students.forEach(student => {
		// Find most recent activity log
		let last_active = "No activity";

		// Get video speed from lesson details
		let video_speed = '-';
		if (student.lesson_details && student.lesson_details.length > 0) {
			// Find the most recent non-null video speed
			for (let ld of student.lesson_details) {
				if (ld.video_speed) {
					video_speed = ld.video_speed;
					break;
				}
			}
		}

		// Unify progress bar with the completed lessons count
		let progress_val = (student.completed_lessons / data.lesson_count) * 100;

		if (lesson_filter && student.specific_lesson) {
			progress_val = student.specific_lesson.completion_percentage;
			if (student.specific_lesson.is_completed && student.specific_lesson.completion_date) {
				last_active = `<span class="text-success">Completed on ${frappe.datetime.str_to_user(student.specific_lesson.completion_date)}</span>`;
			} else if (student.specific_lesson.last_watched) {
				last_active = frappe.datetime.comment_when(student.specific_lesson.last_watched);
			}
		} else {
			// If course is 100% completed, show completion date
			if (student.overall_progress >= 100 && student.completion_date) {
				last_active = `<span class="text-success">Completed on ${frappe.datetime.str_to_user(student.completion_date)}</span>`;
			} else if (student.lesson_details && student.lesson_details.length > 0) {
				// Find most recent lesson activity
				let recent_log = student.lesson_details[0];

				if (recent_log.is_completed && recent_log.completion_date) {
					last_active = `<span class="text-success">Completed on ${frappe.datetime.str_to_user(recent_log.completion_date)}</span>`;
				} else if (recent_log.last_watched_timestamp) {
					last_active = frappe.datetime.comment_when(recent_log.last_watched_timestamp);
				} else {
					last_active = "Just started";
				}
			}
		}

		html += `
			<tr class="student-row" data-student="${student.student}" style="cursor:pointer;">
				<td>
					<div style="font-weight:bold;">${student.student_name}</div>
					<div class="text-muted small">${student.student}</div>
				</td>
				<td>
					<div class="progress" style="height: 20px;">
						<div class="progress-bar ${get_progress_color(progress_val)}" role="progressbar"
							style="width: ${progress_val}%"
							aria-valuenow="${progress_val}" aria-valuemin="0" aria-valuemax="100">
							${progress_val.toFixed(1)}%
						</div>
					</div>
				</td>
				<td>${student.completed_lessons} of ${data.lesson_count} completed</td>
				<td><span class="badge" style="background: ${video_speed !== '-' ? '#17a2b8' : '#6c757d'}; color: white;">${video_speed}</span></td>
				<td>${last_active}</td>
			</tr>
			<tr class="student-details-row" id="details-${student.student}" style="display:table-row;">
				<td colspan="5" style="background:#f8f9fa; padding:20px;">
					${render_student_details(student, lesson_filter)}
				</td>
			</tr>
		`;
	});

	html += `</tbody></table>`;
	$('#students-table').html(html);

	// Add click handler for expandable rows
	$('.student-row').off('click').on('click', function () {
		let student_id = $(this).data('student');
		let details_row = $(`#details-${student_id}`);

		// Toggle visibility - use hide/show instead of fade for table rows
		if (details_row.is(':visible')) {
			details_row.hide();
		} else {
			details_row.show();
		}
	});
}

function render_student_details(student, lesson_filter) {
	let details_html = '<div class="row">';

	if (lesson_filter) {
		// Show specific lesson details if lesson filter is active
		details_html += `<div class="col-md-12"><h5>Lesson Activity Details</h5></div>`;
		if (student.lesson_details && student.lesson_details.length > 0) {
			details_html += render_lesson_list(student.lesson_details);
		} else {
			details_html += `<div class="col-md-12 text-muted">No activity recorded yet</div>`;
		}
	} else {
		// Show all lessons for this student
		details_html += `<div class="col-md-12"><h5>All Lessons Progress</h5></div>`;
		if (student.lesson_details && student.lesson_details.length > 0) {
			details_html += render_lesson_list(student.lesson_details);
		} else {
			details_html += `<div class="col-md-12 text-muted">No lessons started yet</div>`;
		}
	}

	details_html += '</div>';
	return details_html;
}

function render_lesson_list(lessons) {
	let html = '<div class="col-md-12"><table class="table table-sm table-striped">';
	html += `
		<thead>
			<tr>
				<th>Lesson</th>
				<th>Progress</th>
				<th>Video Speed</th>
				<th>Quiz Attempts</th>
				<th>Quiz Score</th>
				<th>Last Activity</th>
			</tr>
		</thead>
		<tbody>
	`;

	lessons.forEach(lesson => {
		let lesson_title = lesson.lesson_title || lesson.lesson || 'Unknown';
		let progress = lesson.completion_percentage || 0;
		let video_speed = lesson.video_speed || 'N/A';
		let quiz_attempts = lesson.quiz_attempts || 0;
		let quiz_score = lesson.quiz_best_score ? `${lesson.quiz_best_score}%` : 'N/A';
		let quiz_passed = lesson.quiz_passed_at_attempt ? `(✓ at attempt ${lesson.quiz_passed_at_attempt})` : '';
		let last_activity = lesson.last_watched_timestamp ?
			frappe.datetime.comment_when(lesson.last_watched_timestamp) : 'Never';

		let status_badge = '';
		if (lesson.is_completed) {
			status_badge = '<span class="badge badge-success">Completed</span>';
		} else if (progress > 0) {
			status_badge = '<span class="badge badge-warning">In Progress</span>';
		} else {
			status_badge = '<span class="badge badge-secondary">Not Started</span>';
		}

		html += `
			<tr>
				<td>
					<div>${lesson_title}</div>
					<div class="small text-muted">${status_badge}</div>
				</td>
				<td>
					<div class="progress" style="height: 15px; width: 100px;">
						<div class="progress-bar ${get_progress_color(progress)}"
							style="width: ${progress}%">
							${progress.toFixed(0)}%
						</div>
					</div>
				</td>
				<td>${video_speed}</td>
				<td>${quiz_attempts > 0 ? quiz_attempts : '-'}</td>
				<td>
					${quiz_score}
					<div class="small text-success">${quiz_passed}</div>
				</td>
				<td class="small">${last_activity}</td>
			</tr>
		`;
	});

	html += '</tbody></table></div>';
	return html;
}

function get_progress_color(percentage) {
	if (percentage >= 100) return 'bg-success';
	if (percentage >= 50) return 'bg-info';
	if (percentage > 0) return 'bg-warning';
	return 'bg-secondary';
}
