Usage
---
*add info 

About mapping
---

List of supported Kubernetes components:
* Deployment:
    * spec with replicas, selector and template of a Pod
        * include containers with name, image, port, resources, args, command
* Service
    *  spec with clusterIP, externalIPs, ports

All components contains required labels, selectors and names.
***
Table of mapping:  
  
| TOSCA | Kubernetes|  
| ------------- |:--------------| 
| private_address| Service: spec: clusterIP|
| public_address| Service: spec: externalIPs|   
| host: num_cpus| Deployment: spec: template: spec: containers: args| 
| host: mem_size:|Deployment: spec: template: spec: containers: resources: limits: memory|
| endpoint: protocol |Service: spec: ports: protocol|
| endpoint: port|Service: spec: ports: port|
| endpoint: port_name|Service:spec:ports:targetPort|
|os: type| Deployment: spec: template: spec: containers: image|
|os: distribution|Deployment: spec: template: spec: containers: image|
|os: version|Deployment: spec: template: spec: containers: image|
|scalable: min_instances|Deployment: spec: replicas

Figure of mapping:

![picture](kubernetes/Tosca_map.png)