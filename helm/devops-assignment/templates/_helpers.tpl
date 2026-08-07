{{/*
Full name of an app component. Falls back to the chart name for the app names.
*/}}
{{- define "devops-assignment.fullname" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels shared by every resource in the chart.
*/}}
{{- define "devops-assignment.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
`part-of` label shared by every component.
*/}}
{{- define "devops-assignment.partOf" -}}
app.kubernetes.io/part-of: devops-assignment
{{- end }}
