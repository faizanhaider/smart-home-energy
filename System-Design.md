# Scalable Real-time Analytics — Smart Home Energy Monitoring

**Goal:** Design a scalable, highly-available architecture for real-time aggregations and alerts for a smart-home system ingesting millions of telemetry points/hour from thousands of devices.

We will:

* Replace direct per-request Postgres queries for telemetry (Postgres remains for device metadata only e.g. Device information (Name, Model, Location etc.)).
* Provide scalable real-time pipeline, fast read paths for analytics API, and an alerting system.

---

## 📌 Problem Summary

* **Current state:** Analytics Service queries PostgreSQL directly per request for telemetry aggregations and alerts. (DeviceDetails page to show graphs and chats)
* **Issue:** High latency and degraded response times during peak hours due to heavy analytic queries on Postgres. (Postgres may be overwhelmed with these input from iOT devcies and might become unavailabel for other services like auth etc)
* **Requirements:**

  * Real-time aggregations and alerts.
  * Handle millions of telemetry events/hour and scale with devices.
  * Durable raw data storage for auditing and historical batch analytics. (Assuming that we need historical data to show historical records)
  * Keep device metadata in Postgres; telemetry should move to a purpose-built store.
  
---

## 🏗️ High-level Architecture

1. **Device Ingress**
   Devices push telemetry via **AWS IoT Core** (MQTT) or **API Gateway + ALB** (HTTP). - Didn't work with MQTT but seems like right choice based on data availble on web

2. **Streaming Layer**

   * IoT Rules → **Amazon Kinesis Data Streams** (low-latency) or **Kinesis Data Firehose**.

3. **Real-time Analytics Engine**

   * **Amazon Kinesis Data Analytics (Apache Flink)** performs windowed aggregations.
   * Writes to:

     * **Amazon ElastiCache (Redis)** → fast reads for API. - We can use this data to push to realtime update to user
     * **Amazon Timestream** or **DynamoDB** → historical retention. - Becaues of nosql structure of DynamoDB and already used it might be better approach

4. **Durable Raw Storage**

   * **Kinesis Firehose** delivers raw telemetry to **Amazon S3**.

5. **Alerting & Events**

   * Analytics job detects conditions → emits events to **Amazon EventBridge** / **Amazon SNS**.
   * Alerts delivered via SNS (email, SMS, push).

6. **Analytics API / Dashboard**

   * Queries **Redis** for recent aggregates.
   * Queries **Timestream/DynamoDB** for historical data.
   * Enriches results with Postgres metadata.

7. **Monitoring & Observability**

   * **CloudWatch** for metrics/logs.
   * **X-Ray** for tracing.
   * **CloudTrail** for auditing.

```
Devices → AWS IoT Core → Kinesis Data Streams → KDA (Flink) → {Redis, Timestream, EventBridge, S3}
                                                        |→ Alerts → SNS → Users
Postgres (metadata) → API enriches results
API → Redis (fast) / Timestream (historical)
```

---

## ✅ Why These Choices

* **AWS IoT Core:** secure device comms (MQTT, device auth).
* **Kinesis + Flink:** scalable streaming, event-time semantics.
* **Redis (ElastiCache):** ultra-low latency for dashboards.
* **Timestream:** purpose-built for time-series telemetry.
* **S3 + Athena:** cheap long-term analytics.
* **SNS/EventBridge:** reliable alert/event fan-out.
* **Postgres only for metadata:** avoids performance issues with telemetry scale.

---

## 🗂️ Data Model

### Telemetry Event

```json
{
  "device_id": "string",
  "timestamp": "ISO8601",
  "metrics": {"power_w": 12.3, "voltage_v": 230},
  "meta": {"firmware": "1.0.3", "location": "kitchen"}
}
```

### Aggregated Record (Windowed)
Because we are storing historical data in s3 we can trim down window to daily 
```json
{
  "device_id": "string",
  "window_start": "ISO8601",
  "window_end": "ISO8601",
  "avg_power_w": 11.2,
  "max_power_w": 20.3,
  "sum_energy_wh": 3.5
}
```

### Device Metadata (Postgres)

```
device_id (PK), owner_id, model, installed_at, timezone, location, config
```

---

## 🔑 Component Pseudocode

### IoT → Kinesis (Rule)

AWS IoT Rule forwards messages to `telemetry-stream`.

### Enrichment Lambda (optional)

```python
def handler(event, context):
    for rec in event['Records']:
        payload = decode(rec['kinesis']['data'])
        meta = get_device_metadata(payload['device_id'])
        enriched = {**payload, 'device_meta': meta}
        put_to_kinesis(enriched, 'telemetry-enriched')
```

### Kinesis Data Analytics (Flink)

```python
from pyflink.datastream import StreamExecutionEnvironment, TimeCharacteristic
from pyflink.datastream.connectors import FlinkKinesisConsumer
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.typeinfo import Types
from pyflink.datastream.window import TumblingEventTimeWindows
from pyflink.common import Time


def aggregate_reducer(e1, e2):
    # Example reducer: merge fields, adjust to your aggregation logic
    return {
        "device_id": e1["device_id"],
        "max_power_w": max(e1["max_power_w"], e2["max_power_w"])
    }


class CustomWindowFunction:
    def apply(self, key, window, inputs, out):
        aggregated = list(inputs)[-1]  # last reduced value

        device_id = key
        write_to_redis(device_id, aggregated)
        write_to_timestream(device_id, aggregated)

        if aggregated["max_power_w"] > threshold:
            emit_alert(device_id, aggregated)


# --- placeholder sinks ---
def write_to_redis(device_id, aggregated):
    print(f"Redis write: {device_id}, {aggregated}")


def write_to_timestream(device_id, aggregated):
    print(f"Timestream write: {device_id}, {aggregated}")


def emit_alert(device_id, aggregated):
    print(f"ALERT: {device_id} exceeded threshold with {aggregated}")


threshold = 1000  # example

# --- setup execution environment ---
env = StreamExecutionEnvironment.get_execution_environment()
env.set_stream_time_characteristic(TimeCharacteristic.EventTime)

# Replace with your actual consumer setup (region, stream name, etc.)
consumer = FlinkKinesisConsumer(
    stream_name="telemetry-enriched",
    deserialization_schema=SimpleStringSchema(),
    properties={
        "aws.region": "us-east-1",
        "flink.stream.initpos": "LATEST"
    }
)

stream = env.add_source(consumer).map(
    lambda x: eval(x),  # TODO: replace eval with proper JSON deserialization
    output_type=Types.MAP(Types.STRING(), Types.PICKLED_BYTE_ARRAY())
)

stream \
    .assign_timestamps_and_watermarks(...) \
    .key_by(lambda event: event["device_id"]) \
    .window(TumblingEventTimeWindows.of(Time.minutes(1))) \
    .reduce(aggregate_reducer, CustomWindowFunction())

env.execute("Kinesis Telemetry Processing")

```

### Redis Layout

```
agg:device:{device_id}:latest → hash (last N windows)
agg:device:{device_id}:window:{start} → JSON
```

### Alerting Lambda

```python
def handler(event, context):
    for record in event['Records']:
        alert = parse(record['body'])
        key = f"alert:{alert['device_id']}:{alert['window_start']}"
        if not seen_before(key):
            publish_sns(alert_topic, alert)
            write_alert_record(alert)
```

### Analytics API (Fast Reads)

```ts
app.get('/devices/:id/metrics/realtime', async (req,res) => {
  const deviceId = req.params.id;
  const recent = await redis.hgetall(`agg:device:${deviceId}:latest`);
  if (recent) return res.json({source: 'redis', data: recent});

  const rows = await timestream.query(...);
  return res.json({source: 'timestream', data: rows});
});
```

---

## 🚀 Migration Plan

1. Add **IoT → Kinesis** ingest pipeline.
2. Deploy enrichment Lambda (optional).
3. Create Kinesis Analytics job (aggregations).
4. Populate **Redis** & **Timestream** with aggregates.
5. Switch API read path from Postgres → Redis/Timestream.
6. Stop writing telemetry to Postgres.
7. Decommission telemetry tables (keep metadata only).

---

## ⚙️ Operational Considerations

* **Scaling:** Kinesis shards & Flink scaling. Redis in cluster mode.
* **Exactly-once:** Flink stateful operators + idempotent writes.
* **Late events:** Flink event-time + watermarks.
* **Backpressure:** Kinesis buffering, retry policies.
* **Security:** IAM least privilege, KMS encryption, IoT X.509.
* **Cost:** Tune shard count, retention policies, and Redis cluster size.

---

## 📊 Key Metrics

* Kinesis throughput & iterator age
* KDA checkpoint lag & state size
* Redis hit rate, memory usage
* Timestream query latency
* API response times (p50, p95, p99)
* Alert delivery latency

---

## ⚠️ Failure Modes

* **Consumer lag:** auto-scale KDA.
* **Redis eviction:** configure eviction + persist to Timestream.
* **Write failures:** buffer to S3 & retry.
* **Schema drift:** version payloads.

---

## 🔄 Alternatives

* **Amazon MSK** instead of Kinesis → more control, more ops. Didn't read but this alternative was easy to follow
* **OpenSearch** for flexible queries → less efficient for time-series.
* **DynamoDB Streams + Lambda** → simpler, but lacks advanced windowing.

---

## 💰 AWS Resource Checklist

* AWS IoT Core
* Kinesis (Data Streams, Firehose)
* Kinesis Data Analytics (Flink)
* ElastiCache (Redis)
* Timestream
* S3 + Athena
* SNS / EventBridge
* Lambda (enrichment, alerts)
* API Gateway / ECS / Fargate
* CloudWatch, X-Ray

---

## 🧪 Testing Plan

* Unit tests for aggregation logic.
* Integration tests with telemetry simulator.
* Load tests at expected peak throughput.
* Canary rollout comparing Postgres vs new pipeline.

---

## 🔮 Next Steps

* Multi-region deployment for keeping cost low.
* User-configurable alerting rules in DynamoDB.

---

### 📎 Appendix: Quick Pseudocode

* **Flink Aggregation** — see Kinesis Data Analytics section.
* **API Read Fallback** — see Analytics API section.

flowchart LR
    subgraph Devices
        D[IoT Devices]
    end

    subgraph Ingress
        IOT[AWS IoT Core (MQTT)]
        API[API Gateway + ALB (HTTP)]
    end

    subgraph Stream
        KDS[Kinesis Data Streams]
        KF[Kinesis Firehose]
    end

    subgraph Analytics
        KDA[Kinesis Data Analytics (Flink)]
        Redis[(ElastiCache Redis)]
        Timestream[(Timestream/DynamoDB)]
        S3[(S3 Raw Storage)]
    end

    subgraph Alerts
        EB[EventBridge]
        SNS[SNS Notifications]
    end

    subgraph API
        APISVC[Analytics API / Dashboard]
        PG[(Postgres - Device Metadata)]
    end

    %% connections
    D --> IOT
    D --> API

    IOT --> KDS
    API --> KDS
    KDS --> KDA
    KDS --> KF --> S3

    KDA --> Redis
    KDA --> Timestream
    KDA --> EB --> SNS

    APISVC --> Redis
    APISVC --> Timestream
    APISVC --> PG
