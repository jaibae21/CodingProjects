/*
	CS424 2019
	 simple.go
	 Beth Allen
	 A simple structure example (objects) using some methods

------------------------------------------------------------
*/
package Testing

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
)

/* a simple structure/object */

type Student struct {
	firstName string
	somevalue float64
}

/****************************************************************/
/* String() method, when applied to a Student object (s) will format
   its internal data into a string    */
/****************************************************************/
func (s Student) String() string {
	return fmt.Sprintf("%10s: %6.1f ", s.firstName, s.somevalue)
}

/****************************************************************/
/* GetAValue()
   A method to return the somevalue of a Student (s)
/****************************************************************/
func (s Student) GetAValue() float64 {
	return s.somevalue
}

/****************************************************************/
/* Initialize()
   A method to initialize the data fields of a student
   WHAT IS THE * for?
/****************************************************************/
func (s *Student) Initialize(name string, value float64) {
	s.firstName = name
	s.somevalue = value
}

/****************************************************************/
/* Body of main program driver */
/****************************************************************/
func main() {
	/* variables used in the main program */

	var keyboard *bufio.Scanner
	var myStudent Student
	var name string
	var estat error
	var fileName string
	var inFile *os.File

	keyboard = bufio.NewScanner(os.Stdin)

	fmt.Print("\nEnter a name: ")
	keyboard.Scan()
	name = keyboard.Text()
	fmt.Print("\nEnter a number: ")
	keyboard.Scan()
	number, _ := strconv.ParseFloat(keyboard.Text(), 64) /* what is the diff between := and = ? */
	/* what is _ used for? */
	myStudent.Initialize(name, number)

	fmt.Print("\nYour student data is: ")
	fmt.Println(myStudent)

	fmt.Println("\nNow I will open a file. Enter the filename: ")
	keyboard.Scan()
	fileName = keyboard.Text()
	inFile, estat = os.Open(fileName)
	if estat != nil {
		fmt.Println("\nI was unable to open the file named " + fileName)
		fmt.Println("Exiting program.")
		os.Exit(1)
	} else {
		fmt.Println("\nI was able to open the file named " + fileName)
	}
	defer inFile.Close() /* this ensures the file closes if there is an unanticipated failure later */

	/* to read from a file you need to attach a bufio.Scanner object to it,
	   something like this,

	   filelines = bufio.NewScanner(inFile)
	   Then you can call .Scan() on filelines just like you can the
	   keybaoard scanner above
	*/

	inFile.Close()
	fmt.Println("\nEnd Program - goodbye!")
}
