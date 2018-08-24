import os
from jinja2 import Environment, FileSystemLoader

cfn_path = os.environ['cfn_template_dir']
input_jinja2_file = os.environ['input_jinja2_file']
output_cfn_template = os.environ['output_cfn_template']
num_copy_lambda_workers = os.environ['num_copy_lambda_workers']
environment = Environment(autoescape=False, loader=FileSystemLoader(cfn_path))

def main():
    print('Generating Cloudformation template: {} from jinja2 template: {}{}'.format(output_cfn_template, cfn_path, input_jinja2_file))
    with open(output_cfn_template, 'w') as f:
        context = {'workers': range(int(num_copy_lambda_workers))}
        output = environment.get_template(input_jinja2_file).render(context)
        f.write(output)

if __name__ == '__main__':
    main()
 