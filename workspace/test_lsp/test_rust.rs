// Test Rust file for LSP autocomplete testing
//
// This file demonstrates LSP features:
// - Keyword autocomplete
// - Type autocomplete
// - Std library autocomplete
// - Macro autocomplete

use std::collections::HashMap;
// Type 'std::' to see standard library modules
// Type 'std::collections::' to see collection types

fn main() {
    // Type 'println' followed by '!' to see macro autocomplete
    println!("Hello, LSP!");

    // Type 'let ' to see keyword autocomplete
    let mut numbers: Vec<i32> = Vec::new();
    // Type 'Vec<' to see Vec methods autocomplete

    numbers.push(1);
    numbers.push(2);
    numbers.push(3);

    // Type 'String::' to see String static methods
    let text = String::from("test");

    // Type 'Option<' to see Option enum
    let maybe_value: Option<i32> = Some(42);

    match maybe_value {
        Some(value) => println!("Value: {}", value),
        None => println!("No value"),
    }

    // Demonstrate diagnostics
    // This should trigger a warning about unwrap()
    let result: Result<i32, &str> = Ok(100);
    let value = result.unwrap();  // LSP should warn about this

    // Type 'vec!' to see macro autocomplete
    let items = vec![1, 2, 3, 4, 5];

    // Type 'std::fs::' to see filesystem operations
    // let contents = std::fs::read_to_string("file.txt");
}

fn calculate_sum(numbers: &[i32]) -> i32 {
    // Type 'fn ' to see keyword autocomplete
    let mut sum = 0;

    // Type 'for ' to see loop keywords
    for num in numbers {
        sum += num;
    }

    sum
}

struct Person {
    name: String,
    age: u32,
}

impl Person {
    // Type 'impl ' to see implementation keywords
    fn new(name: String, age: u32) -> Self {
        Person { name, age }
    }

    fn greet(&self) {
        println!("Hello, my name is {}", self.name);
    }
}
