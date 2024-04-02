use std::env::{args, Args};

fn main() {
    let mut args: Args = args();

    match args.len() {
        // no arguments passed
        1 => {
            panic!("Try passing some arguments!");
        }
        2 | 3 => {
            panic!("Ok, and what should I do with that?")
        }
        4 => {}
        _ => {
            panic!("I'm not that smart to handle this. Sorry!")
        }
    }

    let first_argument = args.nth(1).unwrap();
    let lhs = match first_argument.parse::<f32>() {
        Ok(first) => first,
        Err(error) => panic!(
            "Left hand side '{first_argument}' is not a number. Error: {:?}",
            error
        ),
    };

    let op: char = args.nth(0).unwrap().chars().next().unwrap();

    let third_argument = args.nth(0).unwrap();
    let rhs = match third_argument.parse::<f32>() {
        Ok(third) => third,
        Err(error) => panic!(
            "Right hand side '{third_argument}' is not a number. Error: {:?}",
            error
        ),
    };

    let result = operate(op, lhs, rhs);

    println!("{} {} {} = {}", lhs, op, rhs, result);
}

fn operate(op: char, lhs: f32, rhs: f32) -> f32 {
    match op {
        '+' | 'a' => lhs + rhs,
        '-' => lhs - rhs,
        '/' => lhs / rhs,
        '*' | 'X' | 'x' => lhs * rhs,
        _ => panic!("I don't know how to compute with '{op}'."),
    }
}
