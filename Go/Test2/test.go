/*
Name: Jaiden Gann
Date: 6/30/23
Class: CS424
File Name: test.go
Description: A program that will read input data consisting of students grade information.

	Based on the input it will calculate the grades for each student.

Test Environment: Windows using GoLand
*/
package main

import (
	"bufio"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
)

type Student struct {
	FirstName      string
	LastName       string
	TestGrades     []int
	HomeworkGrades []int
	WeightedGrade  float64
}

func (s *Student) CalculateAverageTestGrade() float64 {
	sum := 0
	for _, grade := range s.TestGrades {
		sum += grade
	}
	return float64(sum) / float64(len(s.TestGrades))
}
func (s *Student) CalculateAverageHwkGrade() float64 {
	sum := 0
	for _, grade := range s.HomeworkGrades {
		sum += grade
	}
	return float64(sum) / float64(len(s.HomeworkGrades))
}
func (s *Student) CalculateAverageWeightedGrade(weightTest, weightHwk float64) {
	avgTest := s.CalculateAverageTestGrade()
	avgHwk := s.CalculateAverageHwkGrade()
	weightTest = weightTest / 100 // divide by 100 to make decimal
	weightHwk = weightHwk / 100
	s.WeightedGrade = (avgTest * weightTest) + (avgHwk * weightHwk)
}
func main() {
	var keyboard *bufio.Scanner
	var inFile *os.File
	var fileName string
	var weightHwk float64
	var estat error

	keyboard = bufio.NewScanner(os.Stdin)

	// Program Introduction
	fmt.Print("\nGradebook calculator test program\nA students grade information will be read from an input file that you provide.\n")
	// Prompt for a file to be opened
	fmt.Println("\nEnter a file to be opened: ")
	keyboard.Scan()
	fileName = keyboard.Text()

	// Prompt for weighted %
	fmt.Print("Enter the % amount to weight test in overall avg: ")
	keyboard.Scan()
	weightTest, _ := strconv.ParseFloat(keyboard.Text(), 64)
	weightHwk = 100 - weightTest
	fmt.Printf("\nTests will be weighted %.2f, Homework will be weighted %0.2f", weightTest, weightHwk)

	//Prompt for number of tests and hwks
	fmt.Print("\nHow many homework assignments are there? ")
	keyboard.Scan()
	hwkNumberFloat, _ := strconv.ParseFloat(keyboard.Text(), 64)
	hwkNumber := int(hwkNumberFloat) // convert to int
	fmt.Print("How many test grades are there? ")
	keyboard.Scan()
	testNumberFloat, _ := strconv.ParseFloat(keyboard.Text(), 64)
	testNumber := int(testNumberFloat) // convert to int

	// Open file
	inFile, estat = os.Open(fileName)
	if estat != nil {
		fmt.Println("\nUnable to open the file named " + fileName)
		fmt.Println("Exiting program.")
		os.Exit(1)
	}
	defer inFile.Close()

	// Read the data and assign it in the struct
	var students []Student
	//lineCnt := 0
	scanner := bufio.NewScanner(inFile)
	for scanner.Scan() {
		line := scanner.Text()        //get name line
		s := strings.Split(line, " ") //splits on spaces

		firstName := s[0]
		lastName := s[1]
		scanner.Scan()                     //scan for another line
		testLine := scanner.Text()         //associate line as test grade line
		tg := strings.Split(testLine, " ") //split on spaces

		scanner.Scan()                    //scan for another line
		hwkLine := scanner.Text()         //associate line as homework grade line
		hg := strings.Split(hwkLine, " ") //split on spaces

		//convert grades from strings to ints
		var testGrades []int
		for _, tg := range tg {
			grade, estat := strconv.Atoi(strings.TrimSpace(tg))
			if estat != nil {
				fmt.Println("Error converting grade: ", estat)
				return
			}
			testGrades = append(testGrades, grade)
		}
		var hwkGrades []int
		for _, hg := range hg {
			hwkGrade, estat := strconv.Atoi(strings.TrimSpace(hg))
			if estat != nil {
				fmt.Println("Error converting grade: ", estat)
				return
			}
			hwkGrades = append(hwkGrades, hwkGrade)
		}
		// Populate Struct
		student := Student{
			FirstName:      firstName,
			LastName:       lastName,
			TestGrades:     testGrades,
			HomeworkGrades: hwkGrades,
		}
		students = append(students, student)
	}
	// Sort the structure - break ties with first name
	sort.Slice(students, func(i, j int) bool {
		if students[i].LastName != students[j].LastName {
			return students[i].LastName < students[j].LastName
		}
		return students[i].FirstName < students[j].FirstName
	})

	// Calculate Overall Avg and print it first
	overallAvg := 0.0
	for _, student := range students {
		student.CalculateAverageWeightedGrade(weightTest, weightHwk)
		overallAvg += student.WeightedGrade
	}
	classAverage := overallAvg / float64(len(students))
	// TODO: Improve Formatting
	// Print the Gradebook
	fmt.Printf("\nGRADE REPORT --- %d STUDENTS FOUND IN FILE\n", len(students))
	fmt.Printf("TEST WEIGHT: %.1f%%\n", weightTest)
	fmt.Printf("HOMEWORK WEIGHT: %.1f%%\n", weightHwk)
	fmt.Printf("OVERALL AVERAGE is %.1f\n\n", classAverage)

	fmt.Printf("%-20s %-15s %-15s %-15s\n", "STUDENT NAME", "TESTS", "HOMEWORKS", "AVG")
	fmt.Println(strings.Repeat("-", 60))
	for _, student := range students {
		// Calculate Average Weighted Grade for each student
		student.CalculateAverageWeightedGrade(weightTest, weightHwk)
		// Name
		fmt.Printf("%s, %s : ", student.LastName, student.FirstName)
		//Test Grades and number there were
		avgTestGrade := student.CalculateAverageTestGrade()
		testGradesStr := fmt.Sprintf("    %.1f (%d)", avgTestGrade, len(student.TestGrades))
		fmt.Printf("%-15s ", testGradesStr)
		// Homework Grades and number there were
		avgHwkGrade := student.CalculateAverageHwkGrade()
		hwkGradesStr := fmt.Sprintf("   %.1f (%d)", avgHwkGrade, len(student.HomeworkGrades))
		fmt.Printf("%-15s ", hwkGradesStr)
		// Overall Weighted Grade
		fmt.Printf("   %.1f", student.WeightedGrade)
		//Missing Assignments
		if len(student.HomeworkGrades) < hwkNumber {
			fmt.Printf(" ** may be missing a homework **")
		}
		if len(student.TestGrades) < testNumber {
			fmt.Printf(" ** may be missing a test **")
		}
		fmt.Println()
	}
	/*	Debug
		for _, student := range students {
			student.CalculateAverageWeightedGrade(weightTest, weightHwk)
			fmt.Printf("First Name: %s, Last Name: %s\n", student.FirstName, student.LastName)
			fmt.Println("Test Grades:", student.TestGrades)
			fmt.Println("Hwk Grades:", student.HomeworkGrades)
			fmt.Printf("Average Test Grade: %.2f\n", student.CalculateAverageTestGrade())
			fmt.Printf("Average Hwk Grade: %.2f\n", student.CalculateAverageHwkGrade())
			fmt.Printf("Weighted Grade: %.2f\n", student.WeightedGrade)
		}
	*/
}
