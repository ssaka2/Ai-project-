// Healthprobe checks trusted operator-supplied HTTP endpoints concurrently.
package main

import (
 "context"
 "encoding/json"
 "flag"
 "fmt"
 "net/http"
 "net/http/httptest"
 "net/url"
 "os"
 "sync"
 "time"
)

type Result struct {
 URL string `json:"url"`
 Healthy bool `json:"healthy"`
 Status int `json:"status"`
 Milliseconds int64 `json:"milliseconds"`
 Error string `json:"error,omitempty"`
}

func Probe(ctx context.Context, urls []string, workers int, timeout time.Duration) ([]Result,error) {
 if workers<1 || workers>32 || timeout<=0 || timeout>time.Minute || len(urls)==0 || len(urls)>1000 { return nil,fmt.Errorf("supply 1–1000 URLs, 1–32 workers, and timeout between 0 and 1 minute") }
 for _,raw:=range urls {
  u,err:=url.Parse(raw)
  if err!=nil || (u.Scheme!="http" && u.Scheme!="https") || u.Hostname()=="" || u.User!=nil || u.Fragment!="" { return nil,fmt.Errorf("invalid HTTP endpoint; credentials and fragments are not allowed") }
 }
 client:=&http.Client{Timeout:timeout,CheckRedirect:func(_ *http.Request,_ []*http.Request)error{return http.ErrUseLastResponse}}
 results:=make([]Result,len(urls)); jobs:=make(chan int); var wg sync.WaitGroup
 for range workers { wg.Add(1); go func(){defer wg.Done();for i:=range jobs {
  started:=time.Now(); result:=Result{URL:urls[i]}
  req,err:=http.NewRequestWithContext(ctx,http.MethodGet,urls[i],nil)
  if err==nil { var response *http.Response; response,err=client.Do(req);if response!=nil { result.Status=response.StatusCode;result.Healthy=response.StatusCode>=200 && response.StatusCode<300;response.Body.Close() } }
  if err!=nil {result.Error=err.Error()};result.Milliseconds=time.Since(started).Milliseconds();results[i]=result
 }}() }
 for i:=range urls {jobs<-i};close(jobs);wg.Wait();return results,nil
}

func main(){
 workers:=flag.Int("workers",4,"maximum simultaneous requests (1–32)")
 timeout:=flag.Duration("timeout",2*time.Second,"per-request timeout, at most 1m")
 demo:=flag.Bool("demo",false,"check a disposable local HTTP server")
 flag.Parse(); endpoints:=flag.Args()
 if *demo {server:=httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){w.WriteHeader(http.StatusOK)}));defer server.Close();endpoints=[]string{server.URL+"/health"}}
 results,err:=Probe(context.Background(),endpoints,*workers,*timeout)
 if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ");if err:=enc.Encode(results);err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(2)}
 for _,r:=range results {if !r.Healthy {os.Exit(1)}}
}
