# Job Status Monitoring

Jobs that produce data (Airflow DAGs, GitHub Actions workflows, cron scripts)
write a small JSON status file after each run. The catalog website shows
which jobs are failing, stuck or stale. The file format is specified in
[job-status-spec.md](https://github.com/DataHerb/dataherb-explorer/blob/main/docs/job-status-spec.md).

```bash
dataherb status emit --target s3://bucket/_dataherb/status/ \
  --job-id sales-export --status running --expected-interval P1D --max-duration PT2H
# ... run the job ...
dataherb status emit --target s3://bucket/_dataherb/status/ \
  --job-id sales-export --status success --dataset sales-daily:11680 --metric rows_written=11680
```

The second call completes the run the first one started. From Python:

```python
from dataherb.catalog.status import emit, store_for_target

store, prefix = store_for_target("s3://bucket/_dataherb/status/")
emit(store, prefix, {"id": "sales-export", "expected_interval": "P1D"}, {"status": "success"})
```

`dataherb status check -c dataherb.config.yml` prints the health of every
job and exits with code 1 when any is failing, stuck or stale.
