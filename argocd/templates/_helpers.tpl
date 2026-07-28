{{- define "argocd.finalizer" -}}
resources-finalizer.argocd.argoproj.io
{{- end -}}

{{- define "argocd.dynamicValuesFile" -}}
values-{{ required "environment is required" .Values.environment }}.yaml
{{- end -}}

{{- define "argocd.automatedSyncPolicy" -}}
automated:
  prune: true
  selfHeal: true
{{- end -}}
