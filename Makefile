NAMESPACE := os-data-platform

.PHONY: forward forward-stop

forward:
	kubectl port-forward svc/storage-seaweedfs-s3 8333:8333 -n $(NAMESPACE) > /dev/null 2>&1 &
	kubectl port-forward svc/warehouse-clickhouse-headless 8123:8123 -n $(NAMESPACE) > /dev/null 2>&1 &
	kubectl port-forward svc/warehouse-clickhouse-headless 9000:9000 -n $(NAMESPACE) > /dev/null 2>&1 &
	kubectl port-forward svc/reporting-superset 8088:8088 -n $(NAMESPACE) > /dev/null 2>&1 &
	kubectl port-forward svc/ingestor-airbyte-server-svc 8001:8001 -n $(NAMESPACE) > /dev/null 2>&1 &

forward-stop:
	pkill -f "kubectl port-forward" || true