from aws_cdk import (
    App,
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_logs as logs,
    aws_iam as iam,
)
from constructs import Construct

class PlotAgentStack(Stack):
    """Stack for deploying Plot Agent to Fargate"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc = ec2.Vpc(
            self,
            "PlotAgentVPC",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                )
            ]
        )

        security_group = ec2.SecurityGroup(
            self,
            "PlotAgentSecurityGroup",
            vpc=vpc,
            description="Security group for Plot Agent containers",
            allow_all_outbound=True,
        )

        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(8501), # For Streamlit traffic
        )

        ecr_repo = ecr.Repository(
            self,
            "PlotAgentRepository",
            repository_name="plot-agent",
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.DESTROY,  # delete repo when stack is deleted
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep last 3 images",
                    max_image_count=3,
                )
            ]
        )

        cluster = ecs.Cluster(
            self,
            "PlotAgentCluster",
            cluster_name="plot-agent-cluster",
            vpc=vpc,
        )

        task_execution_role: iam.IRole = iam.Role(
            self,
            "TaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),  # type: ignore
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ]
        )

        task_role: iam.IRole = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),  # type: ignore
        )

        services_config = [
            {
                "name": "base",
                "app_file": "ui/app.py",
                "test_mode": "false",
                "description": "Base agent",
            },
            {
                "name": "hitl",
                "app_file": "ui/app_hitl.py",
                "test_mode": "false",
                "description": "Human-In-The-Loop agent",
            },
            {
                "name": "hitl-test",
                "app_file": "ui/app_hitl.py",
                "test_mode": "true",
                "description": "HITL test mode agent",
            }
        ]

        for config in services_config:
            self._create_service(
                cluster=cluster,
                security_group=security_group,
                ecr_repo=ecr_repo,
                task_execution_role=task_execution_role,
                task_role=task_role,
                **config,
            )

        # outputs
        CfnOutput(
            self,
            "ECRRepositoryURI",
            value=ecr_repo.repository_uri,
            description="ECR Repository URI",
            export_name="PlotAgentECRRepositoryURI",
        )

        CfnOutput(
            self,
            "ClusterName",
            value=cluster.cluster_name,
            description="ECS Cluster Name",
            export_name="PlotAgentClusterName",
        )

        CfnOutput(
            self,
            "VPCId",
            value=vpc.vpc_id,
            description="VPC ID",
        )

    def _create_service(
        self,
        cluster: ecs.Cluster,
        security_group: ec2.SecurityGroup,
        ecr_repo: ecr.Repository,
        task_execution_role: iam.IRole,
        task_role: iam.IRole,
        name: str,
        app_file: str,
        test_mode: str,
        description: str,
    ) -> ecs.FargateService:
        """Creates a Fargate service with task definition"""

        log_group = logs.LogGroup(
            self,
            f"LogGroup-{name}",
            log_group_name=f"/ecs/plot-agent-{name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )
        task_def = ecs.FargateTaskDefinition(
            self,
            f"TaskDef-{name}",
            cpu=512,
            memory_limit_mib=1024,
            execution_role=task_execution_role,
            task_role=task_role,
        )

        container = task_def.add_container(
            f"Container-{name}",
            image=ecs.ContainerImage.from_ecr_repository(
                ecr_repo, tag="latest"
            ),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="ecs",
                log_group=log_group,
            ),
            environment={
                "DATABASE_URL": "/app/data/database.db",
                "TEST_MODE": test_mode,
            },
            command=[
                "streamlit",
                "run",
                app_file,
                "--server.port=8501",
                "--server.address=0.0.0.0",
                "--server.headless=true",
            ],
        )

        container.add_port_mappings(
            ecs.PortMapping(
                container_port=8501,
                protocol=ecs.Protocol.TCP,
            )
        )

        service = ecs.FargateService(
            self,
            f"Service-{name}",
            cluster=cluster,
            task_definition=task_def,
            service_name=f"plot-agent-{name}",
            desired_count=0,
            assign_public_ip=True,
            security_groups=[security_group],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC,
            ),
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE_SPOT",
                    weight=1,
                )
            ],
        )

        CfnOutput(
            self,
            f"ServiceName-{name}",
            value=service.service_name,
            description=f"{description} service name",
        )

        return service

app = App()
PlotAgentStack(app, "PlotAgentStack")
app.synth()