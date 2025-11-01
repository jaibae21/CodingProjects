#=
File: sample.jl
Beth Allen, Spring 2021

Testing a few Julia features
Reading in a few lines of text, parsing and computing values
Reads same data as programming assignment 2 (Student data, 3 lines per student)

I am Using the macro library Printf for formatting c-style
=#
using Printf
using Statistics

###########################################################
# return the conversion of text to Int64
# will crash with exception if a is not a number!
###########################################################
function getInt(a)
    return parse(Int64,a)
end

###########################################################
# return the average of an array of numbers
###########################################################
function computeAvg(nums)
  return mean(map(getInt,nums))
end

###########################################################
# Main program --
# open a file and read lines of data found in it
# Compute the sum of the values on the 2nd line
# Note: This becomes a very good function candidate, since
# I may want to sum other lines of data
###########################################################

print("\nEnter the name of your input file: ")
myfile = nothing
filename = readline()

try
    global myfile = open(filename)

catch err
    println("\nUnable to open the file: $filename")
	println("Exiting the program\n")
	exit(0)
end

# If the file was opened, process the numbers on the 2nd and 3rd lines

lines = readlines(myfile)
nums = split(lines[2])    # [2] is the 2nd line of data in the test file
print("The words found on line 2 are: ")
println(nums)


nums = map(getInt, nums)  # I wrote getInt, it converts a string to an int
                          # the map operation in julia calls the function on each element
						  # of an array
print("The values converted to integers are: ")
println(nums)

print("The sum is: ")
println(sum(nums))        # julia is a math domain language. There are many built-in ops
                          # that work on numeric data and lists of numbers
println()
println("Goodbye")