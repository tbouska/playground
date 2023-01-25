use std::env::{args, Args};

fn main() {
  let mut args: Args = args();

  let first: String = args.nth(1).unwrap();
  let op: char = args.nth(0).unwrap().chars().next().unwrap();
  let second: String = args.nth(0).unwrap();

  let lhs = first.parse::<f32>().unwrap();
  let rhs = second.parse::<f32>().unwrap();
  let result = operate(op, lhs, rhs);

  println!("{} {} {} = {}", lhs, op, rhs, result);
}

fn operate(op: char, lhs: f32, rhs: f32) -> f32 {
  match op {
    '+' => lhs + rhs,
    '-' => lhs - rhs,
    '/' => lhs / rhs,
    '*' | 'X' | 'x' => lhs * rhs,
    _ => panic!("Invalid op used."),
  }
}
