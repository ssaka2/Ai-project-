use std::{collections::BTreeMap, env, fs, io::{self, Read}, process};
const MAX_BYTES: u64 = 10 * 1024 * 1024;
#[derive(Debug, PartialEq)]
struct Metrics { count: usize, errors: usize, p95_ms: u64, mean_ms: f64 }
fn analyze(input: &str) -> Result<BTreeMap<String, Metrics>, String> {
    if input.len() as u64 > MAX_BYTES { return Err("input exceeds 10 MiB".into()); }
    let mut lines = input.lines();
    if lines.next() != Some("service\tstatus\tlatency_ms") { return Err("expected header: service<TAB>status<TAB>latency_ms".into()); }
    let mut groups: BTreeMap<String, (Vec<u64>, usize)> = BTreeMap::new();
    for (i,line) in lines.enumerate() {
        let fail = || format!("invalid record at line {}", i+2);
        let fields: Vec<_> = line.split('\t').collect();
        if fields.len()!=3 || fields[0].is_empty() || fields[0].len()>64 || !fields[0].bytes().all(|b| b.is_ascii_alphanumeric() || b==b'-' || b==b'_') {return Err(fail());}
        let status: u16 = fields[1].parse().map_err(|_|fail())?;
        let latency: u64 = fields[2].parse().map_err(|_|fail())?;
        if !(100..=599).contains(&status) {return Err(fail());}
        let (latencies, errors) = groups.entry(fields[0].into()).or_default();
        latencies.push(latency); if status>=500 { *errors+=1; }
    }
    if groups.is_empty() { return Err("no records found".into()); }
    Ok(groups.into_iter().map(|(service,(mut times,errors))|{
        times.sort_unstable(); let count=times.len();
        let sum:u128=times.iter().map(|v|u128::from(*v)).sum();
        let p95_ms=times[(95*count).div_ceil(100)-1];
        (service, Metrics{count,errors,p95_ms,mean_ms:sum as f64/count as f64})
    }).collect())
}
fn run() -> Result<(),String> {
    let args:Vec<String>=env::args().skip(1).collect();
    if args.len()!=1 {return Err("usage: log-metrics INPUT.tsv (or - for stdin, --demo for synthetic data)".into());}
    let input = if args[0]=="--demo" {"service\tstatus\tlatency_ms\napi\t200\t20\napi\t503\t100\nworker\t200\t40\n".to_owned()} else {
        let reader:Box<dyn Read>=if args[0]=="-" {Box::new(io::stdin())} else {Box::new(fs::File::open(&args[0]).map_err(|e|e.to_string())?)};
        let mut data=String::new();reader.take(MAX_BYTES+1).read_to_string(&mut data).map_err(|e|e.to_string())?;data
    };
    let groups=analyze(&input)?;
    println!("{{\"services\":[");
    for (i,(name,m)) in groups.iter().enumerate(){
        if i>0 {println!(",");}
        print!("{{\"service\":\"{}\",\"requests\":{},\"server_errors\":{},\"error_rate\":{:.6},\"mean_ms\":{:.3},\"p95_ms\":{}}}",name,m.count,m.errors,m.errors as f64/m.count as f64,m.mean_ms,m.p95_ms);
    }
    println!("\n]}}");Ok(())
}
fn main(){if let Err(e)=run(){eprintln!("{e}");process::exit(2)}}
#[cfg(test)]
mod tests {
 use super::*;
 #[test] fn aggregates_and_orders(){let m=analyze("service\tstatus\tlatency_ms\nb\t200\t20\na\t500\t10\na\t404\t30\n").unwrap();assert_eq!(m["a"],Metrics{count:2,errors:1,p95_ms:30,mean_ms:20.0});assert_eq!(m.keys().next().unwrap(),"a");}
 #[test] fn nearest_rank_p95(){let mut s="service\tstatus\tlatency_ms\n".to_owned();for i in 1..=100{s+=&format!("api\t200\t{i}\n");}assert_eq!(analyze(&s).unwrap()["api"].p95_ms,95);}
 #[test] fn rejects_invalid_rows(){for row in ["api\t600\t2","api\t200\t-1","\t200\t1","bad\"name\t200\t1","api\t200\t1\textra","api\t200\tNaN"]{assert!(analyze(&format!("service\tstatus\tlatency_ms\n{row}\n")).unwrap_err().contains("line 2"));}}
 #[test] fn rejects_empty_or_wrong_header(){for s in ["","wrong\n","service\tstatus\tlatency_ms\n"]{assert!(analyze(s).is_err());}}
 #[test] fn large_latencies_do_not_overflow(){let s=format!("service\tstatus\tlatency_ms\na\t200\t{}\na\t200\t{}\n",u64::MAX,u64::MAX);assert_eq!(analyze(&s).unwrap()["a"].p95_ms,u64::MAX);}
 #[test] fn crlf_supported(){assert_eq!(analyze("service\tstatus\tlatency_ms\r\na\t200\t0\r\n").unwrap()["a"].count,1);}
}
