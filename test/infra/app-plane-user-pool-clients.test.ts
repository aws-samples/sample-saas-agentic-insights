import * as childProcess from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events from 'aws-cdk-lib/aws-events';
import { Template } from 'aws-cdk-lib/assertions';
import { AppPlaneStack } from '../../infra/app-plane-stack';

type UserPoolClientProperties = {
  WriteAttributes?: string[];
};

const clientLogicalIdPrefixes = [
  'BasicTierUserPoolClient',
  'PremiumTierUserPoolClient',
];

describe('tenant user pool client attribute permissions', () => {
  let template: Template;
  let execSyncSpy: jest.SpyInstance;
  let writeFileSyncSpy: jest.SpyInstance;

  beforeAll(() => {
    execSyncSpy = jest.spyOn(childProcess, 'execSync').mockImplementation(
      ((command: string) => {
        if (command === 'aws configure get region') {
          return 'us-east-1\n';
        }

        return '';
      }) as typeof childProcess.execSync,
    );

    const originalWriteFileSync = fs.writeFileSync.bind(fs);
    const generatedAdminEnvironmentPath = path.resolve('web/admin-panel/.env');

    writeFileSyncSpy = jest.spyOn(fs, 'writeFileSync').mockImplementation(
      ((file, data, options) => {
        if (path.resolve(String(file)) === generatedAdminEnvironmentPath) {
          return;
        }

        return originalWriteFileSync(file, data, options);
      }) as typeof fs.writeFileSync,
    );

    const app = new cdk.App({
      context: {
        'aws:cdk:bundling-stacks': [],
      },
    });
    const dependencies = new cdk.Stack(app, 'TestDependencies', {
      env: { account: '111111111111', region: 'us-east-1' },
    });
    const eventBus = new events.EventBus(dependencies, 'EventBus');
    const tenantsTable = new dynamodb.Table(dependencies, 'TenantsTable', {
      partitionKey: {
        name: 'tenant_id',
        type: dynamodb.AttributeType.STRING,
      },
    });

    const stack = new AppPlaneStack(app, 'AppPlaneUnderTest', {
      env: { account: '111111111111', region: 'us-east-1' },
      eventBus,
      tenantsTable,
      controlPlaneApiUrl: 'https://control-plane.example.test',
    });

    template = Template.fromStack(stack);
  });

  afterAll(() => {
    execSyncSpy.mockRestore();
    writeFileSyncSpy.mockRestore();
  });

  test.each(clientLogicalIdPrefixes)(
    '%s allows only legitimate email profile writes',
    (logicalIdPrefix) => {
      const client = findUserPoolClient(template, logicalIdPrefix);

      expect(client.WriteAttributes).toEqual(['email']);
    },
  );
});

function findUserPoolClient(
  template: Template,
  logicalIdPrefix: string,
): UserPoolClientProperties {
  const clients = template.findResources('AWS::Cognito::UserPoolClient');
  const entry = Object.entries(clients).find(([logicalId]) =>
    logicalId.startsWith(logicalIdPrefix),
  );

  expect(entry).toBeDefined();

  return entry![1].Properties as UserPoolClientProperties;
}
