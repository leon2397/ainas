# Kubernetes Deployment

> Deploy AI-NAS Media Manager on a K8s cluster for multi-ARM unified management.

## Architecture

Backend Pod (amd64) <---> ARM Pod(s) (arm64, HPA 1-5)
  Shared PVC: NFS/CephFS 100Gi (RWX) at /nas
  Ingress: ai-nas.local -> backend:8000
  NodePort: 30001 -> arm:8000

## Files

| File | Description |
|------|-------------|
| namespace.yaml | Namespace + labels |
| configmap.yaml | Non-sensitive configuration |
| secret.example.yaml | 敏感数据模板（JWT、密钥）——**真实 secret.yaml 不入库**，需自行复制并填写 |
| windows-deployment.yaml | Backend deploy + service + PVCs |
| arm-deployment.yaml | ARM deploy + service + PVC + affinity |
| arm-service.yaml | NodePort + Ingress + gateway |
| hpa.yaml | HPA + Pod Disruption Budget |

## Quick Deploy

1. 准备密钥：`cp secret.example.yaml secret.yaml`，填入真实 jwt-secret 后再应用
   （`secret.yaml` 已在 .gitignore 中，不会被提交；公网可见的仓库等同于密钥公开）
2. Apply namespace + secrets
3. Apply configmap (customize for your env)
4. Apply windows-deployment.yaml (backend)
5. Apply arm-deployment.yaml + arm-service.yaml + hpa.yaml
6. Verify: kubectl get pods,svc,hpa,pvc -n ai-nas
7. Access via port-forward or Ingress/NodePort

## Scaling

Manual: kubectl scale deployment ai-nas-arm --replicas=3 -n ai-nas
Auto: HPA triggers on CPU 70% / Memory 80%, range 1-5 pods

## Storage

| PVC | Size | Mode | Class | Contents |
|-----|------|------|-------|----------|
| backend-data | 5Gi | RWO | standard | SQLite, ChromaDB |
| nas-storage | 100Gi | RWX | nfs | Photos, albums |
| arm-data | 2Gi | RWO | standard | Models, temp |

## Production Checklist

- [ ] Replace jwt-secret in secret.yaml（从 secret.example.yaml 复制后填写）
- [ ] Configure NFS StorageClass for RWX
- [ ] Set up Ingress TLS
- [ ] Prometheus monitoring
- [ ] Log aggregation (EFK/Loki)
- [ ] PVC backup strategy
- [ ] Test PodDisruptionBudget
