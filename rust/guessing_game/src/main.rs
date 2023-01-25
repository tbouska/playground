use rand::Rng;
use std::io;

fn main() {
    println!("Guess the number 1-100!");
    let secret_number = rand::thread_rng().gen_range(1..=100);
    let mut attempts_count: u8 = 0;
    let mut guessed_number = input_guess();
    while guessed_number != secret_number {
        attempts_count += 1;
        if guessed_number < secret_number {
            println!("Too low, try again.");
            guessed_number = input_guess();
        } else {
            println!("Too high, try again.");
            guessed_number = input_guess();
        }
    }
    println!("Congratulations, you guessed my number after {} attempts!", attempts_count);
}

fn input_guess() -> u8 {
    loop {
        println!("Please input your guess.");
        let mut guess = String::new();
        io::stdin()
            .read_line(&mut guess)
            .expect("Failed to read line");
        match guess.trim().parse::<u8>() {
            Ok(number) => return number,
            Err(_) => continue,
        };
    }
}
