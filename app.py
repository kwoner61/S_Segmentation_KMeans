import os
import sys

import cv2
from PIL import Image
from cytomine import CytomineJob
from cytomine.models import AnnotationCollection, Job, JobData, Term, ImageInstance
from segmentation_job import SegmentationJobCollection
import segscript


def main(argv):
    n = 6
    working_dir = '/CytomineScriptRunner'
    seg_img_names = []
    stats_lists = []

    seg_jobs = SegmentationJobCollection(k=6)

    with CytomineJob.from_cli(argv) as cj:
        update_job_status(cj, 0, 'Starting segmentation job')
        annotations = AnnotationCollection()
        annotations.project = cj.parameters.cytomine_id_project
        annotations.terms = cj.parameters.cytomine_id_terms
        replacement_colors = get_replacement_colors([cj.parameters.color_1,
                                                     cj.parameters.color_2, cj.parameters.color_3,
                                                     cj.parameters.color_4, cj.parameters.color_5,
                                                     cj.parameters.color_6])
        update_job_status(cj, 10, 'Fetching annotations')
        annotations.fetch()

        i = 0
        image_names = []
        num_annotations = len(annotations)
        for annotation in annotations:
            img_name = get_image_file_name(annotation.image, annotations.project, annotation.id)
            seg_image_name = "seg_" + img_name
            img_src = os.path.join(working_dir, img_name)

            mid_progress = 20 + round(i / num_annotations)
            update_job_status(cj, mid_progress, f'Running segmentation for annotation {annotation.id}')
            annotation.dump(dest_pattern=img_src, max_size=cj.parameters.max_size)
            img = cv2.cvtColor(cv2.imread(img_src), cv2.COLOR_BGR2RGB)
            img_uri = upload_job_data(cj.job.id, img_name, img_src)

            seg, stats = segscript.k_means_seg(img, seg_jobs)
            masked, updated_stats = segscript.rgb_mask(n, seg, stats.copy(), replacement_colors)

            Image.fromarray(masked).save(os.path.join(working_dir, seg_image_name))
            masked_uri = upload_job_data(cj.job.id, seg_image_name, os.path.join(working_dir, seg_image_name))

            image_names.append(get_img_src(img_uri))
            seg_img_names.append(get_img_src(masked_uri))
            stats_lists.append(updated_stats)
            os.remove(img_src)
            i += 1

        report_file_path = os.path.join(working_dir, f'combined-k{n}-report.html')
        template_file_path = os.path.join(working_dir, 'combined_report_template.html')
        segscript.generate_combined_report(n, image_names, seg_img_names, stats_lists, report_file_path,
                                           template_file_path)

        update_job_status(cj, 90, 'Uploading report...')
        upload_job_data(cj.job.id, 'Segmentation Report', report_file_path)


def upload_job_data(job_id, key, filename):
    job_data = JobData(job_id, key, filename)
    job_data = job_data.save()
    saved_data = job_data.upload(filename)
    return saved_data.uri().replace('.json', '')


def get_image_file_name(image_id, project_id, annotation_id):
    new_name = ImageInstance(image_id, project_id).fetch(image_id).instanceFilename
    new_name = f'{annotation_id}__{new_name}'
    if len(new_name) < len(f'{annotation_id}') + 2:
        new_name = image_id
    return new_name


def get_seg_image_name(image_name):
    return f'kmeans-seg-{image_name}'


def update_job_status(cytomine_job, progress, message):
    cytomine_job.job.update(status=Job.RUNNING, progress=progress, statusComment=message)


def get_img_src(job_data_uri):
    return f'https://test.cytomine.lamis.life/api/{job_data_uri}/view'


def get_replacement_colors(c_list):
    colors = []
    for c in c_list:
        color = c.split(',')
        color = list(map(int, color))
        colors.append(color)
    return colors


if __name__ == '__main__':
    main(sys.argv[1:])
