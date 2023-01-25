extern crate rand;
extern crate termion;
use std::fs::File;
use std::io::Write;
use std::io::{BufRead, BufReader};
use std::{env, thread, time};
use termion::clear;
use termion::color;

fn census(_world: [[u8; 75]; 75]) -> u16 {
    let mut count = 0;

    for i in 0..74 {
        for j in 0..74 {
            if _world[i][j] == 1 {
                count += 1;
            }
        }
    }
    return count;
}

fn generation(_world: [[u8; 75]; 75]) -> [[u8; 75]; 75] {
    let mut newworld = [[0u8; 75]; 75];

    for i in 0..74 {
        for j in 0..74 {
            let mut count = 0;
            if i > 0 {
                count = count + _world[i - 1][j];
            }
            if i > 0 && j > 0 {
                count = count + _world[i - 1][j - 1];
            }
            if i > 0 && j < 74 {
                count = count + _world[i - 1][j + 1];
            }
            if i < 74 && j > 0 {
                count = count + _world[i + 1][j - 1]
            }
            if i < 74 {
                count = count + _world[i + 1][j];
            }
            if i < 74 && j < 74 {
                count = count + _world[i + 1][j + 1];
            }
            if j > 0 {
                count = count + _world[i][j - 1];
            }
            if j < 74 {
                count = count + _world[i][j + 1];
            }

            newworld[i][j] = 0;

            if (count < 2) && (_world[i][j] == 1) {
                newworld[i][j] = 0;
            }
            if _world[i][j] == 1 && (count == 2 || count == 3) {
                newworld[i][j] = 1;
            }
            if (_world[i][j] == 0) && (count == 3) {
                newworld[i][j] = 1;
            }
        }
    }
    newworld
}

fn populate_from_file(filename: String) -> [[u8; 75]; 75] {
    let mut newworld = [[0u8; 75]; 75];
    let file = File::open(filename).unwrap();
    let reader = BufReader::new(file);
    let mut pairs: Vec<(usize, usize)> = Vec::new();
    for (index, line) in reader.lines().enumerate() {
        let l = line.unwrap();
        let mut words = l.split_whitespace();
        let left = words.next().unwrap();
        let right = words.next().unwrap();
        pairs.push((
            left.parse::<usize>().unwrap(),
            right.parse::<usize>().unwrap(),
        ));
    }

    for i in 0..74 {
        for j in 0..74 {
            newworld[i][j] = 0;
        }
    }

    for (x, y) in pairs {
        if x < 75 && y < 75 {
            newworld[x][y] = 1;
        }
    }
    newworld
}

fn save_to_file(world: [[u8; 75]; 75], filename: String) -> () {
    let mut file = File::create(filename).unwrap();
    for i in 0..74 {
        for j in 0..74 {
            if world[i][j] == 1 {
                writeln!(&mut file, "{} {}", i, j).unwrap();
            }
        }
    }
}

fn displayworld(world: [[u8; 75]; 75]) {
    for i in 0..74 {
        for j in 0..74 {
            if world[i][j] == 1 {
                print!("{yellow}🦋", yellow = color::Fg(color::Yellow));
            } else {
                print!(" ");
            }
        }
        println!("");
    }
}

fn main() {
    let mut world = [[0u8; 75]; 75];
    let mut generations = 0;
    let mut generations_count = 100;

    let args: Vec<String> = env::args().collect();

    if args.len() < 3 {
        // world map not passed
        for i in 0..74 {
            for j in 0..74 {
                if rand::random() {
                    world[i][j] = 1;
                } else {
                    world[i][j] = 0;
                }
            }
        }
    }
    if args.len() > 1 {
        // at least generations count was passed
        let generations_count_arg = env::args().nth(1).unwrap();
        generations_count = generations_count_arg
            .parse::<u16>()
            .unwrap_or(generations_count);
        if args.len() == 3 {
            // we got world map as well
            let filename = env::args().nth(2).unwrap();
            world = populate_from_file(filename);
        }
    }

    println!(
        "Population at generation {} is {}",
        generations,
        census(world)
    );
    for _gens in 0..generations_count {
        let temp = generation(world);
        world = temp;
        generations += 1;
        println!("{}", clear::All);
        displayworld(world);
        println!(
            "{blue}Population at generation {g} is {c}",
            blue = color::Fg(color::Blue),
            g = generations,
            c = census(world)
        );
        thread::sleep(time::Duration::from_millis(125));
    }
    save_to_file(world, "last_world".to_string());
}
