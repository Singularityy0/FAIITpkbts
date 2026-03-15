use base64::{Engine as _, engine::general_purpose::STANDARD};
use flate2::{Compression, write::ZlibEncoder};
use rand::seq::SliceRandom;
use rand::thread_rng;
use rayon::prelude::*;
use rs_poker::core::{Card, Deck, Hand, Rankable};
use std::collections::HashMap;
use std::fs::File;
use std::io::Write;

fn get_board_texture(flop: &[Card]) -> String {
    let mut suits = [0; 4];
    let mut ranks = Vec::with_capacity(3);
    for card in flop {
        suits[card.suit as usize] += 1;
        ranks.push(card.value as u8);
    }
    ranks.sort_unstable();

    let max_suit = suits.iter().max().unwrap();
    let suit_str = match max_suit {
        3 => "Monotone",
        2 => "TwoTone",
        _ => "Rainbow",
    };

    let paired_str = if ranks[0] == ranks[1] || ranks[1] == ranks[2] {
        "Paired"
    } else {
        "Unpaired"
    };

    format!("{}_{}", suit_str, paired_str)
}

fn get_hand_category(hole: &[Card], flop: &[Card]) -> String {
    let mut combined = Vec::with_capacity(5);
    combined.extend_from_slice(hole);
    combined.extend_from_slice(flop);
    let rank = Hand::new_with_cards(combined).rank();
    let dbg_str = format!("{:?}", rank);
    dbg_str.split('(').next().unwrap().to_string()
}

fn main() {
    let iterations = 1_000_000_000_u64;
    let num_threads = num_cpus::get() as u64;
    let iters_per_thread = iterations / num_threads;

    println!(
        "Starting parallel Monte Carlo using {} threads...",
        num_threads
    );

    let thread_results: Vec<(HashMap<String, f64>, HashMap<String, u64>)> = (0..num_threads)
        .into_par_iter()
        .map(|_| {
            let mut local_wins = HashMap::new();
            let mut local_totals = HashMap::new();
            let mut rng = thread_rng();

            for _ in 0..iters_per_thread {
                // Collect deck into a vector and shuffle
                let mut deck: Vec<Card> = Deck::default().into_iter().collect();
                deck.shuffle(&mut rng);

                let hero = [deck.pop().unwrap(), deck.pop().unwrap()];
                let villain = [deck.pop().unwrap(), deck.pop().unwrap()];
                let flop = [
                    deck.pop().unwrap(),
                    deck.pop().unwrap(),
                    deck.pop().unwrap(),
                ];
                let turn = deck.pop().unwrap();
                let river = deck.pop().unwrap();

                // Abstract the state
                let texture = get_board_texture(&flop[..]);
                let category = get_hand_category(&hero[..], &flop[..]);
                let state_key = format!("{}_{}", category, texture);

                let mut hero_hand = Vec::with_capacity(7);
                hero_hand.extend_from_slice(&hero);
                hero_hand.extend_from_slice(&flop);
                hero_hand.push(turn);
                hero_hand.push(river);

                let mut villain_hand = Vec::with_capacity(7);
                villain_hand.extend_from_slice(&villain);
                villain_hand.extend_from_slice(&flop);
                villain_hand.push(turn);
                villain_hand.push(river);

                let hero_rank = Hand::new_with_cards(hero_hand).rank();
                let villain_rank = Hand::new_with_cards(villain_hand).rank();

                let win = if hero_rank > villain_rank {
                    1.0
                } else if hero_rank == villain_rank {
                    0.5
                } else {
                    0.0
                };

                *local_wins.entry(state_key.clone()).or_insert(0.0) += win;
                *local_totals.entry(state_key).or_insert(0) += 1;
            }
            (local_wins, local_totals)
        })
        .collect();

    println!("Simulations complete. Merging thread states...");

    let mut global_wins: HashMap<String, f64> = HashMap::new();
    let mut global_totals: HashMap<String, u64> = HashMap::new();

    for (lw, lt) in thread_results {
        for (k, v) in lw {
            *global_wins.entry(k).or_insert(0.0) += v;
        }
        for (k, v) in lt {
            *global_totals.entry(k).or_insert(0) += v;
        }
    }

    let mut final_equities = HashMap::new();
    for (k, v) in global_wins.iter() {
        let total = *global_totals.get(k).unwrap() as f64;
        let equity = v / total;
        let rounded_equity = (equity * 1000.0).round() / 1000.0;
        final_equities.insert(k.clone(), rounded_equity);
    }

    let json_data = serde_json::to_string(&final_equities).unwrap();
    let mut encoder = ZlibEncoder::new(Vec::new(), Compression::default());
    encoder.write_all(json_data.as_bytes()).unwrap();
    let compressed = encoder.finish().unwrap();
    let encoded = STANDARD.encode(&compressed);

    let mut file = File::create("payload.txt").unwrap();
    file.write_all(encoded.as_bytes()).unwrap();

    println!("Done! Check payload.txt");
}
