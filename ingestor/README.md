# Ingestor

## Add secrets with sources credentials

```shell
kubectl create secret generic ingestor-source-aws \
    --from-literal=key="YOUR_KEY_HERE" \
    --from-literal=secret="YOUR_SECRET_HERE"
```


## Pycharm

Mark ingestor root folder as Source root to improve code navigation