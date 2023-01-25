fn main() {
    let s = String::from("Hello, world!");
    let r = String::from("Zdravím svět!");

    take_ownership(s);
    use_variable(&r);

    //println!("{}", s);
    // this won't compile: s went out of scope because it moved to take_ownership
    //  |
    //2 |     let s = String::from("Hello, world!");
    //|         - move occurs because `s` has type `String`, which does not implement the `Copy` trait
    //...
    //5 |     take_ownership(s);
    //|                    - value moved here
    //...
    //8 |     println!("{}", s);  // this won't compile: s went out of scope because it moved to take_ownership
    //|                    ^ value borrowed here after move
    println!("I can still use r: {}", r);
}

fn take_ownership(s: String) {
    println!("{}", s);
}

fn use_variable(r: &String) {
    println!("{}", *r);
}
