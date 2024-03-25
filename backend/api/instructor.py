""" 
 * instructor.py
 * Last Edited: 3/24/24
 *
 * Contains functions which are applicable to
 * instructor user type
 *
 * Known Bugs:
 * - 
 *
"""

from flask import Blueprint, request, jsonify
from .models import User, Availability, Appointment, AppointmentComment, CourseDetails, CourseMembers, ProgramDetails
from flask_jwt_extended import jwt_required, get_jwt_identity, set_access_cookies, get_jwt, create_access_token
from sqlalchemy import extract, func, or_, and_
from . import db
from datetime import datetime, timedelta, timezone
from .student import get_week_range
from .programs import get_program_type, get_course_name

instructor = Blueprint('instructor', __name__)

# token generator
@instructor.after_request
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            set_access_cookies(response, access_token)
        return response
    except (RuntimeError, KeyError):
        # Case where there is not a valid JWT. Just return the original response
        return response
    
"""""""""""""""""""""""""""""""""""""""""""""""""""""
""             Backend Only Functions              ""
"""""""""""""""""""""""""""""""""""""""""""""""""""""

# return type and isDropins for a program
def get_program_type_and_isDropins(program_id): 
    try: 
        program = ProgramDetails.query.filter_by(id=program_id).first()

        if program:
            returned_attributes = {'name': program.name, 'isDropins': program.isDropins}
            return returned_attributes
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# return the global programs for a instructor
def get_global_programs():
    try:
        user_id = get_jwt_identity()
        instructor = User.query.get(user_id)

        if instructor:
            all_global_programs = ProgramDetails.query.filter(
                and_(ProgramDetails.course_id == None, ProgramDetails.instructor_id == user_id)
            ).all()

            if all_global_programs:
                all_formatted_programs = []

                for program in all_global_programs:
                    program_info = {
                        'id': program.id,
                        'name': program.name,
                        'description': program.description,
                        'duration': program.duration,
                        'physical_location': program.physical_location,
                        'meeting_url': program.meeting_url,
                        'auto_approve_appointments': program.auto_approve_appointments,
                        'max_daily_meetings': program.max_daily_meetings,
                        'max_weekly_meetings': program.max_weekly_meetings,
                        'max_monthly_meetings': program.max_monthly_meetings,
                        'isDropins': program.isDropins,
                        'isRangeBased': program.isRangeBased,
                    }
                    all_formatted_programs.append(program_info)

                all_formatted_programs = {
                    'id': None,
                    'course_name': 'All Courses',
                    'programs': all_formatted_programs
                }

                return all_formatted_programs
            else: 
                return None
        else:
            return None
    except Exception as e:
        return None

# check if date is in correct format
def is_valid_date(date):
    try:
        input_date = datetime.strptime(date, "%Y-%m-%d").date()
        current_date = datetime.now().date()
        return input_date >= current_date
    except ValueError:
        return False
    
# check if time is in correct format
def is_valid_time(time):
    try:
        datetime.strptime(time, "%H:%M")
        return True
    except ValueError:
        return False
    
# validate start and end times
def is_start_time_before_end_time(start_time, end_time):
    try:
        start_datetime = datetime.strptime(start_time, "%H:%M")
        end_datetime = datetime.strptime(end_time, "%H:%M")
        time_difference = end_datetime - start_datetime
        min_time_difference = timedelta(minutes=30)
        if time_difference >= min_time_difference:
            return start_datetime < end_datetime
    except ValueError:
        return False

# validate availability information before before creating it as an availability tuple for the Availability Table
def validate_availability_data_and_course(instructor_id, course_id, availability_id, date, start_time, end_time, isDropins):
    course_id = int(course_id) if course_id and course_id != "null" else None
    
    required_fields = [instructor_id, availability_id, date, start_time, end_time]

    # Check if any required field is missing
    if not all(required_fields):
        return jsonify({"error": "provide all the required fields"}), 404

    # Validate instructor
    instructor = User.query.filter_by(id=instructor_id, account_type='instructor').first()
    if not instructor:
        return jsonify({"error": "instructor not found!"}), 404
    
    if not isDropins:
        if course_id != None:
            courseTuple = CourseDetails.query.filter_by(id=course_id, instructor_id=instructor.id).first()
            if not courseTuple:
                return jsonify({"error": "course not found!"}), 404

    # Validate availability_type
    programTuple = ProgramDetails.query.filter_by(id=availability_id).first()
    if not programTuple:
        return jsonify({"error": f"availability id '{availability_id}' not found"}), 400

    # Validate date
    is_date_valid = is_valid_date(date)
    if not is_date_valid:
        return jsonify({"error": "provide a valid 'YYYY-MM-DD' date format that is not in the past"}), 400

    # Validate start_time and end_time
    if not is_valid_time(start_time) or not is_valid_time(end_time) or not is_start_time_before_end_time(start_time, end_time):
        return jsonify({"error": "provide valid 'HH:MM' time formats, ensure that start_time is before end_time, and that they are at least 30 mins apart"}), 400

    return None  # Data is valid

# check if availability already exists in Availability table
def is_existing_availability_in_course(instructor_id, program_id, date, start_time, end_time):
    existing_availabilities = Availability.query.filter_by(user_id=instructor_id, program_id=program_id, date=date).all()
    
    for existing_availability in existing_availabilities:
        if (start_time < existing_availability.end_time and end_time > existing_availability.start_time):
            return True  # There is a time overlap

    return False  # No time overlap found

# add a availability tuple to the Availabilty Table
def add_instructor_single_availability(course_id, instructor_id, data, physical_location, meeting_url, duration, isDropins):
    try:
        program_id = data.get('id')
        date = data.get('date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        # Validate the data
        validation_result = validate_availability_data_and_course(instructor_id, course_id, program_id, date, start_time, end_time, isDropins)
        if validation_result:
            return validation_result
        
        # Check if the same availability already exists for the instructor
        if is_existing_availability_in_course(instructor_id, program_id, date, start_time, end_time):
            return jsonify({"error": "availability time conflict or it already exists for this instructor"}), 400
        
        current_time = datetime.now() - timedelta(hours=8)
        availability_datetime = datetime.strptime(date + ' ' + start_time, '%Y-%m-%d %H:%M')
        if availability_datetime > current_time:
            # Add the new availability
            new_availability = Availability(
                user_id=instructor_id,
                program_id=program_id,
                date=date,
                start_time=start_time,
                end_time=end_time, 
                status='active'
            )
            db.session.add(new_availability) 
            db.session.commit()
            
            # Generate appointment events
            if not isDropins:
                generate_appointment_tuples(instructor_id, course_id, program_id, date, start_time, end_time, physical_location, meeting_url, new_availability.id, duration)
            return jsonify({"message": "availability added successfully"}), 201
        else:
            return jsonify({"error": "appointment datetime must be in the future"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
        
# Generate appointment events at 30-minute intervals within the specified time range.
def generate_appointment_tuples(instructor_id, course_id, program_id, date, start_time, end_time, physical_location, meeting_url, availability_id, duration):
    try:
        start_datetime = datetime.strptime(start_time, "%H:%M")
        end_datetime = datetime.strptime(end_time, "%H:%M")

        if duration == 0 or not duration:
            new_appointment = Appointment(
                instructor_id=instructor_id,
                appointment_date=date,
                start_time=start_datetime.strftime("%H:%M"),
                end_time=end_datetime.strftime("%H:%M"),
                status="posted",
                physical_location=physical_location,
                meeting_url=meeting_url,
                availability_id=availability_id
            )
            db.session.add(new_appointment)
        else:
            while start_datetime + timedelta(minutes=duration) <= end_datetime:
                new_appointment = Appointment(
                    instructor_id=instructor_id,
                    appointment_date=date,
                    start_time=start_datetime.strftime("%H:%M"),
                    end_time=(start_datetime + timedelta(minutes=duration)).strftime("%H:%M"),
                    status="posted",
                    physical_location=physical_location,
                    meeting_url=meeting_url,
                    availability_id=availability_id
                )
                start_datetime += timedelta(minutes=duration)
                db.session.add(new_appointment)
        
        db.session.commit()
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

"""""""""""""""""""""""""""""""""""""""""""""""""""""
""               Endpoint Functions                ""
"""""""""""""""""""""""""""""""""""""""""""""""""""""

# fetch all of the programs for each course an instructor is in
@instructor.route('/instructor/programs', methods=['GET'])
@jwt_required()
def get_courses():
    try:
        user_id = get_jwt_identity()
        instructor = User.query.get(user_id)
        
        if instructor:
            all_instructor_courses = CourseDetails.query.join(CourseMembers, CourseDetails.id == CourseMembers.course_id).filter_by(user_id=user_id).all()
            course_info = [{'course_id': course.id, 'course_name': course.course_name} for course in all_instructor_courses]

            if all_instructor_courses:

                courses_with_programs = []

                for entry in course_info:
                    course_id = entry['course_id']

                    all_programs_in_course = ProgramDetails.query.filter_by(course_id=course_id).all()
                    course_with_programs = []

                    for program in all_programs_in_course:
                        program_info = {
                            'id': program.id,
                            'name': program.name,
                            'description': program.description,
                            'duration': program.duration,
                            'physical_location': program.physical_location,
                            'meeting_url': program.meeting_url,
                            'auto_approve_appointments': program.auto_approve_appointments,
                            'max_daily_meetings': program.max_daily_meetings,
                            'max_weekly_meetings': program.max_weekly_meetings,
                            'max_monthly_meetings': program.max_monthly_meetings,
                            'isDropins': program.isDropins,
                            'isRangeBased': program.isRangeBased,
                        }
                        course_with_programs.append(program_info)

                    formatTuple = {
                        'id': course_id,
                        'course_name': entry['course_name'],
                        'programs': course_with_programs
                    }

                    courses_with_programs.append(formatTuple)

                global_programs = get_global_programs()
                if global_programs is not None:
                    courses_with_programs.append(global_programs)
                                

                return jsonify(courses_with_programs), 200
            else: 
                return jsonify([]), 204
        else:
            return jsonify({"error": "instructor not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# fetch all of the descriptions for the programs a instructor has
@instructor.route('/instructor/programs/descriptions', methods=['GET'])
@jwt_required()
def get_instructor_programs():
    user_id = get_jwt_identity()

    try: 
        instructor = User.query.filter_by(id=user_id).first()

        if instructor:
            programs = ProgramDetails.query.filter(ProgramDetails.instructor_id==instructor.id).all()
            return jsonify([{
                "id": program.id,
                "name": program.name,
                "description": program.description
            } for program in programs]), 200
        else:
            return jsonify({"error": "Instructor not found"}), 404
    except Exception as e:
        return jsonify({"msg": "Error fetching program description data for instructor", "error": str(e)}), 500

# fetch all appointments a instructor is scheduled for
@instructor.route('/instructor/appointments', methods=['GET'])
@jwt_required()
def get_instructor_appointments_for_course():
    instructor_id = get_jwt_identity()
    meeting_type = request.args.get('type', 'all')
    current_time_pst = datetime.utcnow() - timedelta(hours=8)  # Adjust for PST
    current_date_str = current_time_pst.strftime('%Y-%m-%d')
    current_time_str = current_time_pst.strftime('%H:%M')

    appointments_query = Appointment.query.filter(Appointment.instructor_id == instructor_id)

    if meeting_type in ['upcoming', 'past', 'pending']:
        if meeting_type == 'upcoming':
            appointments_query = appointments_query.filter(
                or_(
                    Appointment.appointment_date > current_date_str,
                    and_(
                        Appointment.appointment_date == current_date_str,
                        Appointment.start_time >= current_time_str
                    )
                ),
                Appointment.status == 'reserved'
            )
        elif meeting_type == 'past':
            appointments_query = appointments_query.filter(
                or_(
                    Appointment.appointment_date < current_date_str,
                    and_(
                        Appointment.appointment_date == current_date_str,
                        Appointment.start_time < current_time_str
                    )
                ),
                Appointment.status.in_(['reserved', 'completed', 'rejected', 'missed', 'canceled'])
            )
        elif meeting_type == 'pending':
            appointments_query = appointments_query.filter(
                or_(
                    Appointment.appointment_date > current_date_str,
                    and_(
                        Appointment.appointment_date == current_date_str,
                        Appointment.start_time >= current_time_str
                    )
                ),
                Appointment.status == 'pending'
            )

    instructor_appointments = []
    appointments = appointments_query.all()

    for appt in appointments:
        student = User.query.get(appt.attendee_id) if appt.attendee_id else None
        student_info = {
            "name": student.name,
            "pronouns": student.pronouns,
            "email": student.email,
        } if student else {}

        program_name = get_program_type(appt.availability.program_details.id)
        course_name = get_course_name(appt.course_id)

        instructor_appointments.append({
            "appointment_id": appt.id,
            "program_id": appt.availability.program_details.id,
            "name": program_name,
            "course_name": course_name,
            "date": appt.appointment_date,
            "start_time": appt.start_time,
            "end_time": appt.end_time,
            "status": appt.status,
            "notes": appt.notes,
            "physical_location": appt.physical_location,
            "meeting_url": appt.meeting_url,
            "instructor": student_info
        })

    return jsonify(instructor_appointments=instructor_appointments), 200
    
# Cancel a specific appointment by its ID if it has been booked
@instructor.route('/instructor/appointments/cancel/<appointment_id>', methods=['POST'])
@jwt_required()
def cancel_appointment(appointment_id):
    try:
        instructor_id = get_jwt_identity()
        appointment = Appointment.query.get(appointment_id)
        instructor = User.query.get(instructor_id)
        
        if not appointment or not instructor:
            return jsonify({"error": "Appointment or instructor doesn't exist"}), 404
        
        # Check if the appointment was booked by this instructor 
        if appointment.status == 'reserved' or appointment.status == 'pending' \
                and appointment.instructor_id == instructor.id:
            current_time = datetime.now() - timedelta(hours=8)
            appointment_datetime = datetime.strptime(appointment.appointment_date + ' ' + appointment.start_time, '%Y-%m-%d %H:%M')
            
            #check if the appointment is in the future
            if appointment_datetime > current_time:
                # Make the appointment available for reservation
                appointment.status = 'canceled'
                db.session.commit()
                return jsonify({"message": "Appointment cancelled successfully"}), 200
            else:
                return jsonify({"error": "Past appointments cannot be cancelled"}), 400
        else:
            return jsonify({"error": "Appointment cannot be cancelled"}), 400
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Create comments for specific appointment as a instructor
@instructor.route('/instructor/appointments/<appointment_id>/comment', methods=['POST'])
@jwt_required()
def create_comment(appointment_id):
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        appointment_comment = data.get('appointment_comment')
        appointment = Appointment.query.get(appointment_id)
        instructor = User.query.get(user_id)
        
        if instructor and appointment:
            new_comment = AppointmentComment(
                appointment_id=appointment_id,
                user_id=user_id,
                appointment_comment=appointment_comment,
                created_at=datetime.now()
            )
            db.session.add(new_comment)
            db.session.commit()
            return jsonify({"message": "comment created successfully"}), 200 
        else:
            return jsonify({"error": "appointment not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Get comments for specific appointment as a instructor
@instructor.route('/instructor/appointments/<appointment_id>/comment', methods=['GET'])
@jwt_required()
def get_comments(appointment_id):
    try:
        user_id = get_jwt_identity()
        appointment = Appointment.query.get(appointment_id)
        instructor = User.query.get(user_id)

        if instructor and appointment:
            comments = AppointmentComment.query.filter_by(appointment_id=appointment_id).join(User, AppointmentComment.user_id == User.id).all()
            comments_list = []
            for comment in comments:
                comment_info = {
                    'id': comment.id,
                    'name': comment.user.name,  # Assuming name is the field name in User table
                    'title': comment.user.title,
                    'pronouns': comment.user.pronouns,
                    'user_id': comment.user_id,
                    'appointment_comment': comment.appointment_comment,
                    'created_at': comment.created_at
                }
                comments_list.append(comment_info)
            return jsonify({"comments": comments_list}), 200
        else:
            return jsonify({"error": "appointment not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Delete comments for specific appointment as a instructor
@instructor.route('/instructor/appointments/<appointment_id>/comment/<comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(appointment_id, comment_id):
    try:
        user_id = get_jwt_identity()
        appointment = Appointment.query.get(appointment_id)
        instructor = User.query.get(user_id)
        comment = AppointmentComment.query.get(comment_id)
        
        if instructor and appointment and comment:
            if comment.user_id == user_id:
                db.session.delete(comment)
                db.session.commit()
                return jsonify({"message": "comment deleted successfully"}), 200
            else:
                return jsonify({"error": "unauthorized"}), 403
        else:
            return jsonify({"error": "appointment or comment not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# fetch the availability for an instructor based on a course_id
@instructor.route('/instructor/availability/<course_id>', methods=['GET'])
@jwt_required()
def get_instructor_availabilities(course_id):
    try:
        # check if instructor exists
        instructor_id = get_jwt_identity()
        instructor = User.query.filter_by(id=instructor_id, account_type='instructor').first()
        if not instructor:
            return jsonify({"error": "instructor not found!"}), 404
        
        current_date = datetime.now().date()

        # get the availability data for the specified instructor
        if course_id:
            if (course_id == '-1'):
                course_id = None

            availability_data = Availability.query.join(ProgramDetails, Availability.program_id == ProgramDetails.id).filter(
                and_(
                    Availability.user_id == instructor_id,
                    Availability.date > str(current_date),
                    ProgramDetails.course_id == course_id
                )
            ).all()
                
            availability_list = []
            for availability in availability_data:
                program = get_program_type_and_isDropins(availability.program_id)
                course_name = get_course_name(availability.program_details.course_id)

                availability_info = {
                    'id': availability.id,
                    'name': program['name'],
                    'course_name': course_name,
                    'date': availability.date,
                    'start_time': availability.start_time,
                    'end_time': availability.end_time,
                    'status': availability.status,
                    'isDropins': program['isDropins']
                }
                availability_list.append(availability_info)
            return jsonify({"instructor_availability": availability_list}), 200
        else:
            return jsonify({"error": "course_id undefined for availability"}), 404
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500
    
# post a set of availability tuples for a course to the Availability Table
@instructor.route('/instructor/availability/<course_id>', methods=['POST'])
@jwt_required()
def add_all_instructor_availability(course_id):
    try:
        data = request.get_json()
        instructor_id = get_jwt_identity()
        allAvailabilties = data.get('availabilities')
        duration = data.get('duration')
        physical_location = data.get('physical_location')
        meeting_url = data.get('meeting_url')
        isDropins = data.get('isDropins')

        for availabilityEntry in allAvailabilties:
            add_instructor_single_availability(course_id, instructor_id, availabilityEntry, physical_location, meeting_url, duration, isDropins)

        return jsonify({"message": "all availability added successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
# update the status of an availability tuple for an instructor
@instructor.route('/instructor/availability/status', methods=['POST'])
@jwt_required()
def update_availability_status():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        availability_id = data.get('availability_id')
        status = data.get('status')

        instructor = User.query.filter_by(id=user_id, account_type='instructor').first()
        if not instructor:
            return jsonify({"error": "instructor not found"}), 404

        availability = Availability.query.filter_by(id=availability_id, user_id=user_id).first()
        if availability:
            parsed_appointment_date = datetime.strptime(availability.date, '%Y-%m-%d')
            start_of_week, end_of_week = get_week_range(availability.date)

            if status == 'inactive':
                availability.status = status
                appointments = Appointment.query.filter_by(availability_id=availability_id, status='posted').all()
                for appointment in appointments:
                    appointment.status = 'inactive'
                db.session.commit()
            elif status == 'active':
                monthly_count = Appointment.query.filter(
                    Appointment.instructor_id == user_id,
                    extract('month', func.date(Appointment.appointment_date)) == parsed_appointment_date.month,
                    extract('year', func.date(Appointment.appointment_date)) == parsed_appointment_date.year,
                    Appointment.status.in_(['reserved', 'pending'])
                ).count()

                weekly_count = Appointment.query.filter(
                    Appointment.instructor_id == user_id,
                    func.date(Appointment.appointment_date).between(start_of_week, end_of_week),
                    Appointment.status.in_(['reserved', 'pending'])
                ).count()

                daily_count = Appointment.query.filter(
                    Appointment.instructor_id == user_id,
                    func.date(Appointment.appointment_date) == parsed_appointment_date,
                    Appointment.status.in_(['reserved', 'pending'])
                ).count()

                program = ProgramDetails.query.filter_by(id=availability.program_id).first()

                error_message = "Meeting limit reached"
                if program.max_monthly_meetings is not None and monthly_count >= program.max_monthly_meetings:
                    error_message = "Monthly meeting limit reached"
                elif program.max_weekly_meetings is not None and weekly_count >= program.max_weekly_meetings:
                    error_message = "Weekly meeting limit reached"
                elif program.max_daily_meetings is not None and daily_count >= program.max_daily_meetings:
                    error_message = "Daily meeting limit reached"

                if error_message != "Meeting limit reached":
                    return jsonify({"error": error_message}), 409

                appointments = Appointment.query.filter_by(availability_id=availability_id, status='inactive').all()
                availability.status = status
                for appointment in appointments:
                    appointment.status = 'posted'
                db.session.commit()
            return jsonify({"message": "status updated successfully"}), 200
        else:
            return jsonify({"error": "availability not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# delete an availability tuple for an instructor
@instructor.route('/instructor/availability/<availability_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_instructor_availabililty(availability_id):
    try:
        instructor_id = get_jwt_identity()        
        instructor = User.query.filter_by(id=instructor_id, account_type='instructor').first() 
        if instructor:
            availability = Availability.query.get(availability_id)

            if availability and availability.user_id == int(instructor_id):
                db.session.delete(availability)
                db.session.commit()
                return jsonify({"message": "delete successful"}), 200
            else:
                return jsonify({"error": "availability not found"}), 404
        else:
            return jsonify({"error": "unauthorized"}), 403
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500