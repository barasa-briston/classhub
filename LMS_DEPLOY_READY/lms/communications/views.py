from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Q
from .models import Ticket, TicketMessage, DiscussionMessage, Notice
from courses.models import Cohort, Enrollment
from assignments.models import Assignment, AssignmentAvailability
from submissions.models import Submission

@login_required
def student_inbox(request):
    if request.user.role != 'STUDENT' and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('home')

    tickets = Ticket.objects.filter(student=request.user).annotate(
        unread_count=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
    ).order_by('-updated_at')

    enrollments = Enrollment.objects.filter(student=request.user).select_related('cohort')
    cohorts = [e.cohort for e in enrollments if e.cohort]

    if request.method == 'POST':
        subject = request.POST.get('subject')
        content = request.POST.get('content')
        cohort_id = request.POST.get('cohort_id')

        if subject and content and cohort_id:
            cohort = get_object_or_404(Cohort, id=cohort_id)
            ticket = Ticket.objects.create(student=request.user, cohort=cohort, subject=subject)
            TicketMessage.objects.create(ticket=ticket, sender=request.user, content=content)

            # Notify Lecturer(s)
            from django.core.mail import send_mail
            from django.conf import settings
            lecturers = cohort.lecturers.all()
            lecturer_emails = [l.email for l in lecturers if l.email]
            if lecturer_emails:
                email_subject = f"New Support Ticket: {subject} - {request.user.username}"
                email_message = f"Student {request.user.username} has created a new support ticket in {cohort.name}.\nSubject: {subject}\nContent: {content}"
                send_mail(email_subject, email_message, settings.DEFAULT_FROM_EMAIL, lecturer_emails, fail_silently=False)

            messages.success(request, "Ticket created successfully.")
            return redirect('ticket-thread', ticket_id=ticket.id)
        else:
            messages.error(request, "All fields are required.")

    return render(request, 'communications/student_inbox.html', {
        'tickets': tickets,
        'cohorts': cohorts,
    })

@login_required
def lecturer_inbox(request):
    if request.user.role != 'LECTURER' and not request.user.is_superuser:
        messages.error(request, "Access denied.")
        return redirect('home')

    if request.user.is_superuser:
        cohorts = Cohort.objects.all()
    else:
        cohorts = Cohort.objects.filter(lecturers=request.user)

    tickets = Ticket.objects.filter(cohort__in=cohorts).annotate(
        unread_count=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
    ).order_by('-updated_at')

    return render(request, 'communications/lecturer_inbox.html', {
        'tickets': tickets,
    })

@login_required
def ticket_thread(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    # Authorization check
    is_student = request.user == ticket.student
    is_lecturer = request.user.is_superuser or request.user in ticket.cohort.lecturers.all()

    if not (is_student or is_lecturer):
        messages.error(request, "Access denied.")
        return redirect('home')

    # Mark unread messages as read
    unread_messages = ticket.messages.filter(is_read=False).exclude(sender=request.user)
    unread_messages.update(is_read=True)

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            TicketMessage.objects.create(ticket=ticket, sender=request.user, content=content)
            ticket.save() # Update updated_at

            # Notify the other party
            from django.core.mail import send_mail
            from django.conf import settings
            
            recipient = None
            if request.user == ticket.student:
                # Notify lecturers
                recipients = [l.email for l in ticket.cohort.lecturers.all() if l.email]
                if recipients:
                    email_subject = f"New Message on Ticket: {ticket.subject}"
                    email_message = f"Student {request.user.username} has replied to the ticket '{ticket.subject}'.\n\nContent:\n{content}"
                    send_mail(email_subject, email_message, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
            else:
                # Notify student
                if ticket.student.email:
                    email_subject = f"New Message on Ticket: {ticket.subject}"
                    email_message = f"Lecturer {request.user.username} has replied to your ticket '{ticket.subject}'.\n\nContent:\n{content}"
                    send_mail(email_subject, email_message, settings.DEFAULT_FROM_EMAIL, [ticket.student.email], fail_silently=False)

            return redirect('ticket-thread', ticket_id=ticket.id)

    messages_list = ticket.messages.all().select_related('sender')

    return render(request, 'communications/ticket_thread.html', {
        'ticket': ticket,
        'messages_list': messages_list,
        'is_student': is_student,
    })

@login_required
def post_discussion(request, assignment_id):
    if request.method == 'POST':
        assignment = get_object_or_404(Assignment, id=assignment_id)
        content = request.POST.get('content')
        if content:
            DiscussionMessage.objects.create(
                assignment=assignment,
                sender=request.user,
                content=content
            )
            messages.success(request, "Discussion message posted.")
        else:
            messages.error(request, "Message cannot be empty.")
            
        # The user was on the submit-assignment view (or similar detail view)
        # We redirect back using HTTP_REFERER
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect('home')

def is_lecturer_or_admin(user):
    return user.is_superuser or getattr(user, 'role', '') in ['LECTURER', 'ADMIN']

@login_required
@user_passes_test(is_lecturer_or_admin)
def assignment_discussion(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    return render(request, 'communications/assignment_discussion.html', {
        'assignment': assignment,
    })

from .forms import NoticeForm

@login_required
@user_passes_test(is_lecturer_or_admin)
def create_notice(request):
    if request.method == 'POST':
        form = NoticeForm(request.POST)
        if form.is_valid():
            notice = form.save(commit=False)
            notice.author = request.user
            notice.save()
            messages.success(request, "Announcement created successfully.")
            return redirect('home')
    else:
        form = NoticeForm()
        
    return render(request, 'communications/create_notice.html', {'form': form})

@login_required
@user_passes_test(is_lecturer_or_admin)
def bulk_congratulate(request):
    """
    Identifies students who have passed all assignments in a cohort and
    allows the admin/lecturer to send them a bulk congratulatory message.
    """
    if request.user.is_superuser or request.user.role in ['ADMIN', 'SUPERADMIN']:
        cohorts = Cohort.objects.all()
    else:
        cohorts = Cohort.objects.filter(lecturers=request.user)

    selected_cohort_id = request.GET.get('cohort')
    students_to_congratulate = []
    
    selected_cohort = None
    if selected_cohort_id:
        try:
            selected_cohort = Cohort.objects.get(id=selected_cohort_id)
            # Find all assignments assigned to this cohort
            availabilities = AssignmentAvailability.objects.filter(cohort=selected_cohort)
            assignment_ids = availabilities.values_list('assignment_id', flat=True)
            total_required = len(assignment_ids)
            
            # Find students in this cohort
            enrollments = Enrollment.objects.filter(cohort=selected_cohort).select_related('student')
            
            for enrollment in enrollments:
                student = enrollment.student
                # Get all marked submissions for this student in this cohort
                student_subs = Submission.objects.filter(
                    student=student, 
                    assignment_id__in=assignment_ids,
                    is_marked=True
                )
                
                completed_count = student_subs.count()
                from django.db.models import Avg
                avg_grade = student_subs.aggregate(Avg('percentage'))['percentage__avg'] or 0
                
                # Criteria: At least 50 assignments AND > 75% average
                if completed_count >= 50 and avg_grade > 75.0:
                    students_to_congratulate.append({
                        'id': student.id,
                        'username': student.get_full_name() or student.username,
                        'raw_username': student.username,
                        'email': student.email or '',
                        'completed': completed_count,
                        'total': total_required,
                        'avg': round(avg_grade, 1)
                    })
        except Cohort.DoesNotExist:
            pass

    # Determine Instructor Name
    instructor_name = "Department of ICT" # Default
    if selected_cohort:
        lecturers = selected_cohort.lecturers.all()
        if lecturers.exists():
            instructor_name = " & ".join([l.get_full_name() or l.username for l in lecturers])
        elif request.user.role == 'LECTURER':
            instructor_name = request.user.get_full_name() or request.user.username

    default_message = f"""Congratulations [name] for successfully completing CCNA 1: Introduction to Networks

Your dedication, consistency, and hard work throughout the course have truly paid off. You have taken an important step toward becoming a skilled networking professional, and this achievement marks the beginning of many greater opportunities in the ICT field.
Keep learning, keep practicing, and continue building your career in networking and technology. Wishing you success in your next Cisco journey and future certifications. See you in CCNA 2 soon.
You can access your certificate through Cisco NetAcad and your badge through Credly.

Congratulations once again! 👏

Regards,
{instructor_name}
{selected_cohort.name if selected_cohort else 'CCNA'} Instructor"""

    if request.method == 'POST':
        student_ids = request.POST.getlist('student_ids')
        title = request.POST.get('title', 'Congratulations on Completing your Course!')
        content = request.POST.get('content', '')
        
        if student_ids and content:
            from django.core.mail import EmailMultiAlternatives
            from django.conf import settings

            notices = []
            emails_sent = 0
            emails_skipped = 0

            # Collect instructor CC emails
            instructor_emails = []
            if selected_cohort:
                for lec in selected_cohort.lecturers.all():
                    if lec.email:
                        instructor_emails.append(lec.email)
            # Also CC the currently logged-in user if they're a lecturer with email
            if request.user.email and request.user.email not in instructor_emails:
                instructor_emails.append(request.user.email)

            for s_id in student_ids:
                try:
                    student = Enrollment.objects.filter(student_id=s_id, cohort=selected_cohort).first().student

                    # Personalized placeholders
                    student_display = student.get_full_name() or student.username
                    personal_content = content.replace("{name}", student_display).replace("[name]", student_display)
                    personal_content = personal_content.replace("{course}", selected_cohort.name).replace("{instructor}", instructor_name)

                    personal_title = title.replace("{name}", student_display).replace("[name]", student_display)
                    personal_title = personal_title.replace("{course}", selected_cohort.name).replace("{instructor}", instructor_name)

                    # 1. LMS Internal Notice (always — individual, no cohort to prevent leaking)
                    notices.append(Notice(
                        title=personal_title,
                        content=personal_content,
                        recipient_id=s_id,
                        author=request.user,
                        cohort=None,  # No cohort — purely individual so other students can't see it
                        is_active=True
                    ))

                    # 2. Email (only if student has an email address)
                    if student.email:
                        try:
                            email_body = f"""{personal_content}

---
This message was sent from the Chuka University CISCO NetAcad Portal.
Please do not reply to this email directly.
"""
                            msg = EmailMultiAlternatives(
                                subject=personal_title,
                                body=email_body,
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                to=[student.email],
                                cc=instructor_emails if instructor_emails else [],
                                reply_to=instructor_emails if instructor_emails else [],
                            )
                            msg.send(fail_silently=False)
                            emails_sent += 1
                        except Exception:
                            emails_skipped += 1
                    else:
                        emails_skipped += 1

                except (AttributeError, Enrollment.DoesNotExist):
                    continue

            Notice.objects.bulk_create(notices)

            summary = f"Congratulations sent to {len(notices)} students via LMS notice."
            if emails_sent:
                summary += f" {emails_sent} email(s) also delivered from cisco@chuka.ac.ke."
            if emails_skipped:
                summary += f" {emails_skipped} student(s) had no email — notice only."
            messages.success(request, summary)
            return redirect('admin-dashboard')
        else:
            messages.error(request, "Please select students and provide a message content.")

    return render(request, 'communications/bulk_congratulate.html', {
        'cohorts': cohorts,
        'selected_cohort': selected_cohort,
        'students': students_to_congratulate,
        'default_message': default_message
    })
