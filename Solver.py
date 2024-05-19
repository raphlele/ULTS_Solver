import pulp
import streamlit as st
import pandas as pd

def solve_schedule(Nd, Np, Nt, Nc, Nr, Ng, days, professors, time_periods, courses, rooms, groups, preference_data, available_time_periods, assigned_courses_groups, room_availability, required_teaching_periods, weekly_teaching_load):
    # Create the problem
    prob = pulp.LpProblem("University_lecture_Timetabling_Model_Pulp", pulp.LpMaximize)

    # Decision variables
    x = pulp.LpVariable.dicts("x", ((d, p, c, g, r, t) for d in days for p in professors for c in courses for g in groups for r in rooms for t in time_periods), cat="Binary")

    # Objective function
    prob += pulp.lpSum(x[d, p, c, g, r, t] * preference_data.get((d, p, t), 0) for d in days for p in professors for c in courses for g in groups for r in rooms for t in time_periods)

    # Constraints
    # 1. Every professor is assigned at most one course, group, and classroom at a time
    for d in days:
        for p in professors:
            for t in time_periods:
                prob += pulp.lpSum(x[d, p, c, g, r, t] for c in courses for g in groups for r in rooms) <= 1

    # 2. For every group, at most one course, professor, and classroom is assigned at a time
    for d in days:
        for g in groups:
            for t in time_periods:
                prob += pulp.lpSum(x[d, p, c, g, r, t] for p in professors for c in courses for r in rooms) <= 1

    # 3. Every classroom is assigned at most one course, professor, and group at a time
    for d in days:
        for r in rooms:
            for t in time_periods:
                prob += pulp.lpSum(x[d, p, c, g, r, t] for p in professors for c in courses for g in groups) <= 1

    # 4. Professors can only be assigned to their assigned courses and groups, and rooms can only be assigned during their available time periods
    for d in days:
        for p in professors:
            for c in courses:
                for g in groups:
                    for r in rooms:
                        for t in time_periods:
                            if (c, g) not in assigned_courses_groups[p] or t not in available_time_periods.get((d, p), []) or t not in room_availability.get((d, r), []):
                                prob += x[d, p, c, g, r, t] == 0 

    # 5. All courses in the curriculum of each student group should be scheduled for the required amount of teaching periods
    for c in courses:
        for g in groups:
            required_periods = required_teaching_periods.get((c, g), 0)
            prob += pulp.lpSum(x[d, p, c, g, r, t] for d in days for p in professors for r in rooms for t in time_periods) == required_periods

    # 6. Each Professor should be assigned to so many teaching periods as his/her weekly teaching load requires
    for p in professors:
        weekly_load = weekly_teaching_load.get(p, 0)
        prob += pulp.lpSum(x[d, p, c, g, r, t] for d in days for c in courses for g in groups for r in rooms for t in time_periods) == weekly_load

    # Solve the problem
    prob.solve()

    # Return the status, objective value, and solution
    return prob.status, pulp.value(prob.objective), [(d, p, c, g, r, t) for d in days for p in professors for c in courses for g in groups for r in rooms for t in time_periods if x[d, p, c, g, r, t].value() > 0]

def main():
    #Some Css lignes to adjust The Background and the Background of the timetable/table
    page_bg_img = """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Rubik+Glitch&display=swap');
            [data-testid="stAppViewContainer"]{
                background-image: url("https://images.pexels.com/photos/1089438/pexels-photo-1089438.jpeg");
                background-size: 100%;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: local;
            }
            [data-testid="stFullScreenFrame"]{
                background-image: url("https://images.pexels.com/photos/1089438/pexels-photo-1089438.jpeg");
                background-size: 100%;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: local;
            }
            #ults-solver{
                font-family: "Rubik Glitch", system-ui;
                font-weight: 400;
                font-style: normal;
            }
            /*color value => color : #0BF5E7  */
        </style>
        """

    st.title("ULTS SOLVER")
    #Allow html and css in streamlit
    st.markdown(page_bg_img, unsafe_allow_html=True)
    # Retrieve input parameters from the user
    Nd = st.sidebar.number_input("Number of days:", min_value=1, step=1)
    Np = st.sidebar.number_input("Number of professors:", min_value=1, step=1)
    Nt = st.sidebar.number_input("Number of time periods:", min_value=1, step=1)
    Nc = st.sidebar.number_input("Number of courses:", min_value=1, step=1)
    Nr = st.sidebar.number_input("Number of rooms:", min_value=1, step=1)
    Ng = st.sidebar.number_input("Number of groups:", min_value=1, step=1)

    # Define the primary sets
    days = range(1, Nd + 1)
    professors = range(1, Np + 1)
    time_periods = range(1, Nt + 1)
    courses = range(1, Nc + 1)
    rooms = range(1, Nr + 1)
    groups = range(1, Ng + 1)

    # Retrieve available time periods for professors
    available_time_periods = {}
    for day in days:
        for professor in professors:
            available_time_periods[(day, professor)] = st.sidebar.multiselect(
                f"Available time periods for Professor {professor} on Day {day}",
                options=range(1, Nt + 1),
                default=[]
            )

    # Retrieve preference data
    preference_data = {}
    for day in days:
        for professor in professors:
            for time_period in time_periods:
                # Set preference to 0 if the time period is not available
                if time_period not in available_time_periods[(day, professor)]:
                    preference_data[(day, professor, time_period)] = 0
                else:
                    preference_data[(day, professor, time_period)] = st.sidebar.slider(
                        f"Preference for Day {day}, Professor {professor}, Time Period {time_period}",
                        min_value=0, max_value=10, value=0
                    )

    # Retrieve assigned courses and groups
    assigned_courses_groups = {}
    for professor in professors:
        assigned_courses_groups[professor] = st.sidebar.multiselect(
            f"Assigned courses and groups for Professor {professor}(Course,Group)",
            options=[(course, group) for course in range(1, Nc + 1) for group in range(1, Ng + 1)],
            default=[]
        )

    # Retrieve room availability data
    room_availability = {}
    for day in days:
        for room in rooms:
            room_availability[(day, room)] = st.sidebar.multiselect(
                f"Available time periods for Room {room} on Day {day}",
                options=range(1, Nt + 1),
                default=[]
            )

    # Retrieve required teaching periods
    required_teaching_periods = {}
    for course in courses:
        for group in groups:
            required_teaching_periods[(course, group)] = st.sidebar.number_input(
                f"Required teaching periods for Course {course} to Group {group}",
                min_value=0,
                step=1
            )

    # Retrieve weekly teaching load
    weekly_teaching_load = {}
    for professor in professors:
        weekly_teaching_load[professor] = st.sidebar.number_input(
            f"Weekly teaching load for Professor {professor}",
            min_value=0,
            step=1
        )

    # Run the scheduler
    if st.sidebar.button("Run Scheduler"):
        status, objective_value, solution = solve_schedule(Nd, Np, Nt, Nc, Nr, Ng, days, professors, time_periods, courses, rooms, groups, preference_data, available_time_periods, assigned_courses_groups, room_availability, required_teaching_periods, weekly_teaching_load)
        
        st.write("Status:", status)
        st.write("Objective value:", objective_value)
        st.write("Solution:")
        
        # Display results in a table
        solution_df = pd.DataFrame(solution, columns=['Day', 'Professor', 'Course', 'Group', 'Room', 'Time Period'])
        # Create a new column for the assignment in the format "P1-C1-G1-R1"
        solution_df['Assignment'] = 'P' + solution_df['Professor'].astype(str) + '-' + 'C' + solution_df['Course'].astype(str) + '-' + 'G' + solution_df['Group'].astype(str) + '-' + 'R' + solution_df['Room'].astype(str)

        # Pivot the DataFrame to create the timetable
        timetable = solution_df.pivot_table(index='Day', columns='Time Period', values='Assignment', aggfunc=lambda x: '\n'.join(x))
        #Show the Results in timetable format and simple table format
        st.write(timetable)
        st.write(solution_df)

if __name__ == "__main__":
    main()
