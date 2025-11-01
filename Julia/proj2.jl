#=
- File: proj2.jl
- Author: Jaiden Gann
- Date: 2023-07-16
- Description: Gradebook that prints report of students in alphabetical and by Highest Average order
- Environment: Windows using Goland with Julia extension and julia 1.9.2
=#
mutable struct Student
    FirstName::String
    LastName::String
    TestGrades::Vector{Int}
    HomeworkGrades::Vector{Int}
    WeightedGrade::Float64
end

function calculate_average_test_grade(student::Student)
    return sum(student.TestGrades) / length(student.TestGrades)
end

function calculate_average_hwk_grade(student::Student)
    return sum(student.HomeworkGrades) / length(student.HomeworkGrades)
end

function calculate_average_weighted_grade!(student::Student, weight_test::Float64, weight_hwk::Float64)
    avg_test = calculate_average_test_grade(student)
    avg_hwk = calculate_average_hwk_grade(student)
    weight_test /= 100  # divide by 100 to make it a decimal
    weight_hwk /= 100
    student.WeightedGrade = avg_test * weight_test + avg_hwk * weight_hwk
end

function main()
    println("Gradebook calculator test program")
    println("A student's grade information will be read from an input file that you provide.")

    # Prompt for a file to be opened
    println("\nEnter a file to be opened: ")
    fileName = readline()

    # Prompt for weighted %
    print("Enter the % amount to weight the test in the overall average: ")
    weight_test = parse(Float64, readline())
    weight_hwk = 100 - weight_test
    println("Tests will be weighted $weight_test, Homework will be weighted $weight_hwk")

    # Prompt for the number of tests and homework assignments
    print("How many homework assignments are there? ")
    hwk_number = parse(Int, readline())
    print("How many test grades are there? ")
    test_number = parse(Int, readline())

    # Open file
    in_file = open(fileName)

    # Read the data and organize it as a matrix
    students = []
    for line in eachline(in_file)
        name_line = split(line, ' ')
        first_name = name_line[1]
        last_name = name_line[2]

        test_line = readline(in_file)
        test_grades = parse.(Int, split(test_line, ' '))

        hwk_line = readline(in_file)
        hwk_grades = parse.(Int, split(hwk_line, ' '))

        student = Student(first_name, last_name, test_grades, hwk_grades, 0.0)
        push!(students, student)
    end
    close(in_file)

    # Sort the students by last name, breaking ties with first name
    sort!(students, by = s -> (lowercase(s.LastName), lowercase(s.FirstName)))

    # Calculate overall average and print it first
    overall_avg = 0.0
    for student in students
        calculate_average_weighted_grade!(student, weight_test, weight_hwk)
        overall_avg += student.WeightedGrade
    end
    class_avg = round(overall_avg / length(students), digits =1)

    # Print the Gradebook
    println("\nGRADE REPORT --- $(length(students)) STUDENTS FOUND IN FILE")
    println("TEST WEIGHT: $weight_test%")
    println("HOMEWORK WEIGHT: $weight_hwk%")
    println("OVERALL AVERAGE is $class_avg\n")
    println("STUDENT NAME\t\tTESTS\t\tHOMEWORKS\t\tAVG")
    println("-" ^ 60)
    for student in students
        # Calculate average weighted grade for each student
        calculate_average_weighted_grade!(student, weight_test, weight_hwk)

        # Test Grades and number
        avg_test_grade = calculate_average_test_grade(student)
        test_grades_str = "$(round(avg_test_grade, digits=1))\t\t($(length(student.TestGrades)))"

        # Homework Grades and number
        avg_hwk_grade = calculate_average_hwk_grade(student)
        hwk_grades_str = "$(round(avg_hwk_grade, digits=1))\t\t($(length(student.HomeworkGrades)))"

        # Overall Weighted Grade
        weighted_grade_str = "$(round(student.WeightedGrade, digits=1))"

        # Missing Assignments
        missing_assignments = ""
        if length(student.HomeworkGrades) < hwk_number
            missing_assignments *= " ** may be missing a homework **"
        end
        if length(student.TestGrades) < test_number
            missing_assignments *= " ** may be missing a test **"
        end

        println("$(student.LastName), $(student.FirstName):\t\t$test_grades_str\t$hwk_grades_str\t$weighted_grade_str\t$missing_assignments")
    end

    # Sort the students in descending order by average grade
    sort!(students, rev = true, by = s -> s.WeightedGrade)

    # Print Second Gradebook
    println("\nSorted by Average, Descending")
    println("STUDENT NAME\t\tTESTS\t\tHOMEWORKS\t\tAVG")
    println("-" ^ 60)
    for student in students
        # Calculate average weighted grade for each student
        calculate_average_weighted_grade!(student, weight_test, weight_hwk)

        # Test Grades and number
        avg_test_grade = calculate_average_test_grade(student)
        test_grades_str = "$(round(avg_test_grade, digits=1))\t\t($(length(student.TestGrades)))"

        # Homework Grades and number
        avg_hwk_grade = calculate_average_hwk_grade(student)
        hwk_grades_str = "$(round(avg_hwk_grade, digits=1))\t\t($(length(student.HomeworkGrades)))"

        # Overall Weighted Grade
        weighted_grade_str = "$(round(student.WeightedGrade, digits=1))"

        # Missing Assignments
        missing_assignments = ""
        if length(student.HomeworkGrades) < hwk_number
            missing_assignments *= " ** may be missing a homework **"
        end
        if length(student.TestGrades) < test_number
            missing_assignments *= " ** may be missing a test **"
        end

        println("$(student.LastName), $(student.FirstName):\t\t$test_grades_str\t$hwk_grades_str\t$weighted_grade_str\t$missing_assignments")
    end
    exit()
end

main()
